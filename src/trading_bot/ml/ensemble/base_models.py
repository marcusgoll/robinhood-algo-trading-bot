"""Base models for hierarchical signal stacking.

Implements diverse neural network architectures (LSTM, GRU, Transformer) that
serve as Layer 1 in the stacking ensemble. Each model captures different patterns:
- LSTM: Long-term temporal dependencies
- GRU: Efficient short-term patterns
- Transformer: Multi-scale attention mechanisms

All models accept 52-dimensional feature vectors and output 3-class predictions.
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from numpy.typing import NDArray


class BaseModel(nn.Module, ABC):
    """Abstract base class for ensemble models.

    All base models must:
    - Accept 52-dimensional input features
    - Output 3-class predictions (BUY/HOLD/SELL)
    - Implement forward() for training
    - Implement predict_proba() for inference
    """

    def __init__(self, input_dim: int = 52, output_dim: int = 3):
        """Initialize base model.

        Args:
            input_dim: Input feature dimension (default: 52)
            output_dim: Number of output classes (default: 3)
        """
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim

    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass producing logits.

        Args:
            x: Input tensor of shape (batch, seq_len, input_dim) or (batch, input_dim)

        Returns:
            Logits of shape (batch, output_dim)
        """
        pass

    def predict_proba(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Predict class probabilities for meta-learner.

        Args:
            x: Input features of shape (n_samples, input_dim) or (n_samples, seq_len, input_dim)

        Returns:
            Probabilities of shape (n_samples, output_dim)
        """
        self.eval()
        with torch.no_grad():
            x_tensor = torch.FloatTensor(x)
            logits = self.forward(x_tensor)
            probs = torch.softmax(logits, dim=-1)
            return probs.cpu().numpy()


class LSTMModel(BaseModel):
    """LSTM-based model for temporal pattern recognition.

    Architecture:
    - 2-layer bidirectional LSTM (128 hidden units)
    - Dropout for regularization (0.3)
    - Fully connected output layer

    Specialization: Captures long-term temporal dependencies in price movements.
    """

    def __init__(
        self,
        input_dim: int = 52,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        output_dim: int = 3
    ):
        """Initialize LSTM model.

        Args:
            input_dim: Input feature dimension
            hidden_dim: LSTM hidden dimension
            num_layers: Number of LSTM layers
            dropout: Dropout probability
            output_dim: Number of output classes
        """
        super().__init__(input_dim, output_dim)

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True
        )

        # Dropout after LSTM
        self.dropout = nn.Dropout(dropout)

        # Output layer (bidirectional doubles hidden size)
        self.fc = nn.Linear(hidden_dim * 2, output_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        for name, param in self.lstm.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)

        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through LSTM.

        Args:
            x: Input of shape (batch, seq_len, input_dim) or (batch, input_dim)

        Returns:
            Logits of shape (batch, output_dim)
        """
        # Handle single feature vector input
        if x.dim() == 2:
            x = x.unsqueeze(1)  # (batch, input_dim) -> (batch, 1, input_dim)

        # LSTM forward pass
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden_dim * 2)

        # Take last timestep output
        last_hidden = lstm_out[:, -1, :]  # (batch, hidden_dim * 2)

        # Dropout and output layer
        out = self.dropout(last_hidden)
        logits = self.fc(out)  # (batch, output_dim)

        return logits


class GRUModel(BaseModel):
    """GRU-based model for efficient sequence processing.

    Architecture:
    - 2-layer bidirectional GRU (128 hidden units)
    - Dropout for regularization (0.3)
    - Fully connected output layer

    Specialization: Efficient short-term pattern detection with fewer parameters than LSTM.
    """

    def __init__(
        self,
        input_dim: int = 52,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        output_dim: int = 3
    ):
        """Initialize GRU model.

        Args:
            input_dim: Input feature dimension
            hidden_dim: GRU hidden dimension
            num_layers: Number of GRU layers
            dropout: Dropout probability
            output_dim: Number of output classes
        """
        super().__init__(input_dim, output_dim)

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # GRU layers
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True
        )

        # Dropout after GRU
        self.dropout = nn.Dropout(dropout)

        # Output layer (bidirectional doubles hidden size)
        self.fc = nn.Linear(hidden_dim * 2, output_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        for name, param in self.gru.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)

        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through GRU.

        Args:
            x: Input of shape (batch, seq_len, input_dim) or (batch, input_dim)

        Returns:
            Logits of shape (batch, output_dim)
        """
        # Handle single feature vector input
        if x.dim() == 2:
            x = x.unsqueeze(1)  # (batch, input_dim) -> (batch, 1, input_dim)

        # GRU forward pass
        gru_out, _ = self.gru(x)  # (batch, seq_len, hidden_dim * 2)

        # Take last timestep output
        last_hidden = gru_out[:, -1, :]  # (batch, hidden_dim * 2)

        # Dropout and output layer
        out = self.dropout(last_hidden)
        logits = self.fc(out)  # (batch, output_dim)

        return logits


class TransformerModel(BaseModel):
    """Transformer-based model for multi-scale attention.

    Architecture:
    - Positional encoding for temporal information
    - Multi-head self-attention encoder (4 heads, 128 dim)
    - Feed-forward network with dropout (0.3)
    - Fully connected output layer

    Specialization: Learns complex cross-feature relationships via attention mechanisms.
    """

    def __init__(
        self,
        input_dim: int = 52,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 512,
        dropout: float = 0.3,
        output_dim: int = 3
    ):
        """Initialize Transformer model.

        Args:
            input_dim: Input feature dimension
            d_model: Dimension of model embeddings
            nhead: Number of attention heads
            num_layers: Number of transformer layers
            dim_feedforward: Dimension of feedforward network
            dropout: Dropout probability
            output_dim: Number of output classes
        """
        super().__init__(input_dim, output_dim)

        self.d_model = d_model
        self.nhead = nhead

        # Input projection
        self.input_projection = nn.Linear(input_dim, d_model)

        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, dropout, max_len=100)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        # Output layers
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(d_model, output_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        nn.init.xavier_uniform_(self.input_projection.weight)
        nn.init.zeros_(self.input_projection.bias)
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through Transformer.

        Args:
            x: Input of shape (batch, seq_len, input_dim) or (batch, input_dim)

        Returns:
            Logits of shape (batch, output_dim)
        """
        # Handle single feature vector input
        if x.dim() == 2:
            x = x.unsqueeze(1)  # (batch, input_dim) -> (batch, 1, input_dim)

        # Project input to d_model dimension
        x = self.input_projection(x)  # (batch, seq_len, d_model)

        # Add positional encoding
        x = self.pos_encoder(x)

        # Transformer encoder
        encoded = self.transformer_encoder(x)  # (batch, seq_len, d_model)

        # Global average pooling over sequence
        pooled = encoded.mean(dim=1)  # (batch, d_model)

        # Output layer
        out = self.dropout(pooled)
        logits = self.fc(out)  # (batch, output_dim)

        return logits


class PositionalEncoding(nn.Module):
    """Positional encoding for Transformer.

    Adds sinusoidal position information to input embeddings.
    """

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 100):
        """Initialize positional encoding.

        Args:
            d_model: Dimension of model embeddings
            dropout: Dropout probability
            max_len: Maximum sequence length
        """
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # Create positional encoding matrix
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model)
        )

        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)

        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional encoding to input.

        Args:
            x: Input tensor of shape (batch, seq_len, d_model)

        Returns:
            Tensor with positional encoding added
        """
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)
