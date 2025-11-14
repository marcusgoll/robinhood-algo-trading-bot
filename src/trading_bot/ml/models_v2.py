"""Advanced model architectures for Phase 3 systematic experiments.

Implements all Tier 1-3 architectures for systematic testing:
- Baseline: LSTM, GRU, Transformer (from ensemble.py)
- Tier 2: CNN-LSTM, Multi-Task LSTM, Attention-LSTM
- Tier 3: Mixture of Experts, Temporal Fusion Transformer (TFT)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional


# =============================================================================
# BASELINE MODELS (from ensemble.py - regression versions)
# =============================================================================

class RegressionLSTM(nn.Module):
    """LSTM for regression (predicts continuous return)."""

    def __init__(
        self,
        input_dim: int = 57,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # x: (batch, input_dim)
        x = x.unsqueeze(1)  # (batch, 1, input_dim)
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])
        return out.squeeze(-1)  # (batch,)


class RegressionGRU(nn.Module):
    """GRU for regression."""

    def __init__(
        self,
        input_dim: int = 57,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3
    ):
        super().__init__()
        self.gru = nn.GRU(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        x = x.unsqueeze(1)  # (batch, 1, input_dim)
        gru_out, _ = self.gru(x)
        out = self.fc(gru_out[:, -1, :])
        return out.squeeze(-1)


class RegressionTransformer(nn.Module):
    """Transformer for regression."""

    def __init__(
        self,
        input_dim: int = 57,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.3
    ):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x):
        x = x.unsqueeze(1)  # (batch, 1, input_dim)
        x = self.input_proj(x)  # (batch, 1, d_model)
        x = self.transformer(x)
        out = self.fc(x[:, -1, :])
        return out.squeeze(-1)


# =============================================================================
# TIER 2: ADVANCED ARCHITECTURES
# =============================================================================

class CNN_LSTM(nn.Module):
    """Hybrid CNN-LSTM architecture.

    1D CNN extracts local patterns from feature sequence.
    LSTM models temporal dependencies over CNN features.
    """

    def __init__(
        self,
        input_dim: int = 57,
        cnn_channels: List[int] = [64, 32],
        lstm_hidden: int = 64,
        lstm_layers: int = 2,
        dropout: float = 0.3,
        sequence_length: int = 20
    ):
        super().__init__()
        self.sequence_length = sequence_length

        # 1D Convolution layers
        self.conv_layers = nn.ModuleList()
        in_channels = input_dim

        for out_channels in cnn_channels:
            self.conv_layers.append(nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1),
                nn.BatchNorm1d(out_channels),
                nn.ReLU(),
                nn.Dropout(dropout)
            ))
            in_channels = out_channels

        # LSTM over CNN features
        self.lstm = nn.LSTM(
            cnn_channels[-1],
            lstm_hidden,
            lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0
        )

        # Output layer
        self.fc = nn.Linear(lstm_hidden, 1)

    def forward(self, x):
        # x: (batch, input_dim) - single feature vector
        # We need to create a sequence for CNN

        batch_size = x.size(0)

        # Repeat to create sequence: (batch, seq_len, input_dim)
        x = x.unsqueeze(1).repeat(1, self.sequence_length, 1)

        # Transpose for Conv1d: (batch, input_dim, seq_len)
        x = x.permute(0, 2, 1)

        # Apply CNN layers
        for conv in self.conv_layers:
            x = conv(x)

        # Back to (batch, seq_len, channels)
        x = x.permute(0, 2, 1)

        # LSTM
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])

        return out.squeeze(-1)


class MultiTaskLSTM(nn.Module):
    """Multi-task LSTM predicting multiple horizons simultaneously.

    Learns shared representations across different prediction horizons.
    """

    def __init__(
        self,
        input_dim: int = 57,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
        horizons: List[int] = [3, 6, 12, 24],
        loss_weights: Optional[List[float]] = None
    ):
        super().__init__()
        self.horizons = horizons
        self.loss_weights = loss_weights or [1.0 / len(horizons)] * len(horizons)

        # Shared LSTM encoder
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Separate prediction heads for each horizon
        self.heads = nn.ModuleDict({
            f"{h}bar": nn.Linear(hidden_dim, 1) for h in horizons
        })

    def forward(self, x):
        # x: (batch, input_dim)
        x = x.unsqueeze(1)  # (batch, 1, input_dim)

        # Shared encoding
        lstm_out, _ = self.lstm(x)
        hidden = lstm_out[:, -1, :]  # (batch, hidden_dim)

        # Multi-horizon predictions
        predictions = {}
        for horizon in self.horizons:
            pred = self.heads[f"{horizon}bar"](hidden)
            predictions[f"{horizon}bar"] = pred.squeeze(-1)

        return predictions

    def compute_loss(self, predictions: Dict[str, torch.Tensor], targets: Dict[str, torch.Tensor]):
        """Compute weighted multi-task loss.

        Args:
            predictions: Dict of predictions per horizon
            targets: Dict of targets per horizon

        Returns:
            Total weighted loss
        """
        total_loss = 0.0
        for i, horizon in enumerate(self.horizons):
            key = f"{horizon}bar"
            loss = F.mse_loss(predictions[key], targets[key])
            total_loss += self.loss_weights[i] * loss

        return total_loss


class AttentionLSTM(nn.Module):
    """LSTM with self-attention mechanism.

    Attention helps model focus on most relevant features.
    """

    def __init__(
        self,
        input_dim: int = 57,
        hidden_dim: int = 64,
        num_layers: int = 2,
        attention_dim: int = 32,
        dropout: float = 0.3
    ):
        super().__init__()

        # LSTM encoder
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, attention_dim),
            nn.Tanh(),
            nn.Linear(attention_dim, 1),
            nn.Softmax(dim=1)
        )

        # Output layer
        self.fc = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, input_dim)
        x = x.unsqueeze(1)  # (batch, 1, input_dim)

        # LSTM encoding
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden_dim)

        # Compute attention weights
        attention_weights = self.attention(lstm_out)  # (batch, seq_len, 1)

        # Apply attention
        context = (lstm_out * attention_weights).sum(dim=1)  # (batch, hidden_dim)

        # Prediction
        context = self.dropout(context)
        out = self.fc(context)

        return out.squeeze(-1)


# =============================================================================
# TIER 3: CUTTING-EDGE ARCHITECTURES
# =============================================================================

class MixtureOfExperts(nn.Module):
    """Mixture of Experts with learned gating.

    Gating network routes inputs to appropriate expert based on features.
    """

    def __init__(
        self,
        input_dim: int = 57,
        expert_configs: Optional[List[Dict]] = None,
        gating_hidden: int = 32,
        dropout: float = 0.3
    ):
        super().__init__()

        # Default expert configurations
        if expert_configs is None:
            expert_configs = [
                {"type": "lstm", "hidden_dim": 64, "num_layers": 2},
                {"type": "gru", "hidden_dim": 64, "num_layers": 2},
                {"type": "transformer", "d_model": 64, "nhead": 4, "num_layers": 2}
            ]

        # Create expert models
        self.experts = nn.ModuleList()
        for config in expert_configs:
            if config["type"] == "lstm":
                self.experts.append(RegressionLSTM(
                    input_dim=input_dim,
                    hidden_dim=config.get("hidden_dim", 64),
                    num_layers=config.get("num_layers", 2),
                    dropout=dropout
                ))
            elif config["type"] == "gru":
                self.experts.append(RegressionGRU(
                    input_dim=input_dim,
                    hidden_dim=config.get("hidden_dim", 64),
                    num_layers=config.get("num_layers", 2),
                    dropout=dropout
                ))
            elif config["type"] == "transformer":
                self.experts.append(RegressionTransformer(
                    input_dim=input_dim,
                    d_model=config.get("d_model", 64),
                    nhead=config.get("nhead", 4),
                    num_layers=config.get("num_layers", 2),
                    dropout=dropout
                ))

        # Gating network
        self.gating = nn.Sequential(
            nn.Linear(input_dim, gating_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(gating_hidden, len(self.experts)),
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        # x: (batch, input_dim)

        # Compute gating weights
        gate_weights = self.gating(x)  # (batch, num_experts)

        # Get predictions from all experts
        expert_predictions = torch.stack([
            expert(x) for expert in self.experts
        ], dim=1)  # (batch, num_experts)

        # Weighted combination
        output = (expert_predictions * gate_weights).sum(dim=1)

        return output


class TemporalFusionTransformer(nn.Module):
    """Simplified Temporal Fusion Transformer.

    Multi-head attention with temporal encoding for multi-horizon forecasting.
    """

    def __init__(
        self,
        input_dim: int = 57,
        hidden_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.3,
        max_encoder_length: int = 60,
        max_prediction_length: int = 12
    ):
        super().__init__()
        self.max_encoder_length = max_encoder_length
        self.max_prediction_length = max_prediction_length

        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # Positional encoding
        self.pos_encoding = nn.Parameter(
            torch.randn(1, max_encoder_length, hidden_dim)
        )

        # Multi-head attention layers
        self.attention_layers = nn.ModuleList([
            nn.MultiheadAttention(
                embed_dim=hidden_dim,
                num_heads=num_heads,
                dropout=dropout,
                batch_first=True
            )
            for _ in range(num_layers)
        ])

        # Feed-forward layers
        self.ff_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim * 4),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim * 4, hidden_dim),
                nn.Dropout(dropout)
            )
            for _ in range(num_layers)
        ])

        # Layer norms
        self.layer_norms1 = nn.ModuleList([
            nn.LayerNorm(hidden_dim) for _ in range(num_layers)
        ])
        self.layer_norms2 = nn.ModuleList([
            nn.LayerNorm(hidden_dim) for _ in range(num_layers)
        ])

        # Output projection
        self.output_proj = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # x: (batch, input_dim)
        batch_size = x.size(0)

        # Create sequence (repeat for simplicity)
        x = x.unsqueeze(1).repeat(1, self.max_encoder_length, 1)
        # x: (batch, seq_len, input_dim)

        # Project to hidden dim
        x = self.input_proj(x)  # (batch, seq_len, hidden_dim)

        # Add positional encoding
        x = x + self.pos_encoding[:, :x.size(1), :]

        # Apply attention and feed-forward layers
        for attn, ff, ln1, ln2 in zip(
            self.attention_layers,
            self.ff_layers,
            self.layer_norms1,
            self.layer_norms2
        ):
            # Multi-head attention with residual
            attn_out, _ = attn(x, x, x)
            x = ln1(x + attn_out)

            # Feed-forward with residual
            ff_out = ff(x)
            x = ln2(x + ff_out)

        # Use last position for prediction
        output = self.output_proj(x[:, -1, :])

        return output.squeeze(-1)


# =============================================================================
# MODEL FACTORY
# =============================================================================

def create_model(model_config: Dict) -> nn.Module:
    """Factory function to create models from config.

    Args:
        model_config: Configuration dict with 'type' and 'params'

    Returns:
        Instantiated model
    """
    model_type = model_config["type"]
    params = model_config.get("params", {})

    model_classes = {
        "regression_lstm": RegressionLSTM,
        "regression_gru": RegressionGRU,
        "regression_transformer": RegressionTransformer,
        "cnn_lstm": CNN_LSTM,
        "multi_task_lstm": MultiTaskLSTM,
        "attention_lstm": AttentionLSTM,
        "moe": MixtureOfExperts,
        "tft": TemporalFusionTransformer,
    }

    if model_type not in model_classes:
        raise ValueError(f"Unknown model type: {model_type}")

    return model_classes[model_type](**params)


if __name__ == "__main__":
    # Test all models
    batch_size = 32
    input_dim = 57
    x = torch.randn(batch_size, input_dim)

    print("Testing all model architectures...")
    print("=" * 80)

    # Baseline models
    for name, model_class in [
        ("LSTM", RegressionLSTM),
        ("GRU", RegressionGRU),
        ("Transformer", RegressionTransformer)
    ]:
        model = model_class(input_dim=input_dim)
        output = model(x)
        params = sum(p.numel() for p in model.parameters())
        print(f"{name:20s} Output shape: {output.shape}, Params: {params:,}")

    # Advanced models
    cnn_lstm = CNN_LSTM(input_dim=input_dim)
    output = cnn_lstm(x)
    params = sum(p.numel() for p in cnn_lstm.parameters())
    print(f"{'CNN-LSTM':20s} Output shape: {output.shape}, Params: {params:,}")

    multi_task = MultiTaskLSTM(input_dim=input_dim, horizons=[3, 6, 12, 24])
    output = multi_task(x)
    params = sum(p.numel() for p in multi_task.parameters())
    print(f"{'Multi-Task LSTM':20s} Output shape: {list(output.values())[0].shape}, Params: {params:,}")

    attn_lstm = AttentionLSTM(input_dim=input_dim)
    output = attn_lstm(x)
    params = sum(p.numel() for p in attn_lstm.parameters())
    print(f"{'Attention LSTM':20s} Output shape: {output.shape}, Params: {params:,}")

    moe = MixtureOfExperts(input_dim=input_dim)
    output = moe(x)
    params = sum(p.numel() for p in moe.parameters())
    print(f"{'Mixture of Experts':20s} Output shape: {output.shape}, Params: {params:,}")

    tft = TemporalFusionTransformer(input_dim=input_dim)
    output = tft(x)
    params = sum(p.numel() for p in tft.parameters())
    print(f"{'TFT':20s} Output shape: {output.shape}, Params: {params:,}")

    print("\nAll models tested successfully!")
