"""Create order execution tables

Revision ID: 001
Revises:
Create Date: 2025-10-17

Tables: orders, fills, execution_logs
Enums: order_type_enum, order_status_enum, action_enum
Security: RLS policies for trader isolation

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create order execution infrastructure:
    1. Enum types for order_type, order_status, action
    2. orders table with validation constraints
    3. fills table for execution records
    4. execution_logs table for immutable audit trail
    5. Indexes for performance
    6. RLS policies for trader isolation
    """

    # ========== ENUMS ==========
    # Create enum types
    op.execute("""
        CREATE TYPE order_type_enum AS ENUM ('MARKET', 'LIMIT', 'STOP')
    """)

    op.execute("""
        CREATE TYPE order_status_enum AS ENUM (
            'PENDING', 'FILLED', 'PARTIAL', 'REJECTED', 'CANCELLED'
        )
    """)

    op.execute("""
        CREATE TYPE action_enum AS ENUM (
            'SUBMITTED', 'APPROVED', 'EXECUTED', 'FILLED',
            'REJECTED', 'CANCELLED', 'RECOVERED'
        )
    """)

    # ========== ORDERS TABLE ==========
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique order identifier'),
        sa.Column('trader_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Reference to trader (FK to traders table)'),
        sa.Column('symbol', sa.String(10), nullable=False,
                  comment='Stock symbol (e.g., AAPL, MSFT)'),
        sa.Column('quantity', sa.Integer, nullable=False,
                  comment='Number of shares to trade'),
        sa.Column('order_type',
                  postgresql.ENUM('MARKET', 'LIMIT', 'STOP', name='order_type_enum'),
                  nullable=False,
                  comment='Type of order (MARKET/LIMIT/STOP)'),
        sa.Column('price', sa.Numeric(10, 2), nullable=True,
                  comment='Limit price (null for market orders)'),
        sa.Column('stop_loss', sa.Numeric(10, 2), nullable=True,
                  comment='Stop loss price for risk management'),
        sa.Column('take_profit', sa.Numeric(10, 2), nullable=True,
                  comment='Take profit price for risk management'),
        sa.Column('status',
                  postgresql.ENUM('PENDING', 'FILLED', 'PARTIAL', 'REJECTED', 'CANCELLED',
                                  name='order_status_enum'),
                  nullable=False,
                  server_default='PENDING',
                  comment='Current order status'),
        sa.Column('filled_quantity', sa.Integer, nullable=False,
                  server_default='0',
                  comment='Quantity filled so far'),
        sa.Column('average_fill_price', sa.Numeric(10, 2), nullable=True,
                  comment='Average price of all fills'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When order was submitted'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Last modification time'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True,
                  comment='Order expiration time (if timeout set)'),

        # Check constraints
        sa.CheckConstraint('quantity > 0', name='ck_orders_quantity_positive'),
        sa.CheckConstraint(
            'price IS NULL OR price > 0',
            name='ck_orders_price_positive'
        ),
        sa.CheckConstraint(
            'filled_quantity >= 0',
            name='ck_orders_filled_quantity_nonnegative'
        ),
        sa.CheckConstraint(
            'filled_quantity <= quantity',
            name='ck_orders_filled_lte_quantity'
        ),
        sa.CheckConstraint(
            "order_type = 'MARKET' OR price IS NOT NULL",
            name='ck_orders_limit_requires_price'
        ),

        # Foreign key constraint (assuming traders table exists)
        # sa.ForeignKeyConstraint(['trader_id'], ['traders.id'],
        #                        name='fk_orders_trader_id',
        #                        ondelete='CASCADE'),

        comment='Order requests with full execution lifecycle tracking'
    )

    # Indexes for orders table
    op.create_index(
        'idx_orders_trader_created',
        'orders',
        ['trader_id', sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_orders_status',
        'orders',
        ['status'],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_orders_trader_status',
        'orders',
        ['trader_id', 'status'],
        postgresql_using='btree'
    )

    # ========== FILLS TABLE ==========
    op.create_table(
        'fills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique fill identifier'),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Reference to order'),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When fill occurred'),
        sa.Column('quantity_filled', sa.Integer, nullable=False,
                  comment='Shares filled in this execution'),
        sa.Column('price_at_fill', sa.Numeric(10, 2), nullable=False,
                  comment='Execution price'),
        sa.Column('venue', sa.String(50), nullable=False,
                  comment='Exchange name (NYSE, NASDAQ, Mock)'),
        sa.Column('commission', sa.Numeric(10, 2), nullable=False,
                  server_default='0',
                  comment='Transaction fee'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Record creation time'),

        # Check constraints
        sa.CheckConstraint(
            'quantity_filled > 0',
            name='ck_fills_quantity_positive'
        ),
        sa.CheckConstraint(
            'price_at_fill > 0',
            name='ck_fills_price_positive'
        ),
        sa.CheckConstraint(
            'commission >= 0',
            name='ck_fills_commission_nonnegative'
        ),

        # Foreign key constraint
        sa.ForeignKeyConstraint(
            ['order_id'], ['orders.id'],
            name='fk_fills_order_id',
            ondelete='CASCADE'
        ),

        comment='Individual fill events when order executes'
    )

    # Indexes for fills table
    op.create_index(
        'idx_fills_order',
        'fills',
        ['order_id'],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_fills_timestamp',
        'fills',
        [sa.text('timestamp DESC')],
        postgresql_using='btree'
    )

    # ========== EXECUTION LOGS TABLE ==========
    op.create_table(
        'execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique log identifier'),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Reference to order'),
        sa.Column('trader_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Reference to trader'),
        sa.Column('action',
                  postgresql.ENUM('SUBMITTED', 'APPROVED', 'EXECUTED', 'FILLED',
                                  'REJECTED', 'CANCELLED', 'RECOVERED',
                                  name='action_enum'),
                  nullable=False,
                  comment='Action that occurred'),
        sa.Column('status',
                  postgresql.ENUM('PENDING', 'FILLED', 'PARTIAL', 'REJECTED', 'CANCELLED',
                                  name='order_status_enum'),
                  nullable=True,
                  comment='Order status at time of action'),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Precise moment of event'),
        sa.Column('reason', sa.Text, nullable=True,
                  comment='Why action occurred (e.g., error message)'),
        sa.Column('retry_attempt', sa.Integer, nullable=True,
                  comment='Retry attempt number (0=initial, 1=first retry)'),
        sa.Column('error_code', sa.String(50), nullable=True,
                  comment='Exchange error code if applicable'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Record creation time'),

        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ['order_id'], ['orders.id'],
            name='fk_execution_logs_order_id',
            ondelete='CASCADE'
        ),
        # sa.ForeignKeyConstraint(
        #     ['trader_id'], ['traders.id'],
        #     name='fk_execution_logs_trader_id',
        #     ondelete='CASCADE'
        # ),

        comment='Immutable append-only audit trail for compliance (SEC Rule 4530)'
    )

    # Indexes for execution_logs table
    op.create_index(
        'idx_execution_logs_trader_timestamp',
        'execution_logs',
        ['trader_id', sa.text('timestamp DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_execution_logs_order',
        'execution_logs',
        ['order_id'],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_execution_logs_action',
        'execution_logs',
        ['action'],
        postgresql_using='btree'
    )

    # ========== ROW LEVEL SECURITY (RLS) ==========
    # Enable RLS on all three tables
    op.execute("ALTER TABLE orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fills ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY")

    # RLS Policy: Traders can only see their own orders
    op.execute("""
        CREATE POLICY orders_trader_isolation ON orders
        FOR ALL
        USING (trader_id = current_setting('app.user_id', true)::uuid)
    """)

    # RLS Policy: Traders can only see fills for their own orders
    op.execute("""
        CREATE POLICY fills_trader_isolation ON fills
        FOR ALL
        USING (
            order_id IN (
                SELECT id FROM orders
                WHERE trader_id = current_setting('app.user_id', true)::uuid
            )
        )
    """)

    # RLS Policy: Traders can only see their own execution logs
    op.execute("""
        CREATE POLICY execution_logs_trader_isolation ON execution_logs
        FOR ALL
        USING (trader_id = current_setting('app.user_id', true)::uuid)
    """)

    # RLS Policy: Prevent updates and deletes on execution_logs (immutable)
    op.execute("""
        CREATE POLICY execution_logs_immutable ON execution_logs
        FOR UPDATE
        USING (false)
    """)

    op.execute("""
        CREATE POLICY execution_logs_immutable_delete ON execution_logs
        FOR DELETE
        USING (false)
    """)


def downgrade() -> None:
    """
    Rollback migration:
    1. Drop RLS policies
    2. Drop tables (cascade)
    3. Drop enum types
    """

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS execution_logs_immutable_delete ON execution_logs")
    op.execute("DROP POLICY IF EXISTS execution_logs_immutable ON execution_logs")
    op.execute("DROP POLICY IF EXISTS execution_logs_trader_isolation ON execution_logs")
    op.execute("DROP POLICY IF EXISTS fills_trader_isolation ON fills")
    op.execute("DROP POLICY IF EXISTS orders_trader_isolation ON orders")

    # Drop tables (CASCADE will drop dependent fills and execution_logs)
    op.drop_table('execution_logs')
    op.drop_table('fills')
    op.drop_table('orders')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS action_enum")
    op.execute("DROP TYPE IF EXISTS order_status_enum")
    op.execute("DROP TYPE IF EXISTS order_type_enum")
