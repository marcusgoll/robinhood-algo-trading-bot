-- Row Level Security (RLS) Policies for Order Execution
-- Purpose: Enforce trader data isolation at database level
-- Tables: orders, fills, execution_logs

-- =============================================================================
-- ORDERS TABLE POLICIES
-- =============================================================================

-- Enable RLS on orders table
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Policy: Traders can only access their own orders
-- Applies to: SELECT, INSERT, UPDATE, DELETE
CREATE POLICY orders_trader_isolation ON orders
FOR ALL
USING (trader_id = current_setting('app.user_id', true)::uuid);

-- Policy: Admin/Compliance bypass (optional)
-- Uncomment if admin role exists
-- CREATE POLICY orders_admin_access ON orders
-- FOR ALL
-- TO admin_role
-- USING (true);

-- =============================================================================
-- FILLS TABLE POLICIES
-- =============================================================================

-- Enable RLS on fills table
ALTER TABLE fills ENABLE ROW LEVEL SECURITY;

-- Policy: Traders can only see fills for their own orders
-- Uses subquery to check order ownership
CREATE POLICY fills_trader_isolation ON fills
FOR ALL
USING (
    order_id IN (
        SELECT id FROM orders
        WHERE trader_id = current_setting('app.user_id', true)::uuid
    )
);

-- =============================================================================
-- EXECUTION LOGS TABLE POLICIES
-- =============================================================================

-- Enable RLS on execution_logs table
ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Traders can only see their own execution logs
CREATE POLICY execution_logs_trader_isolation ON execution_logs
FOR ALL
USING (trader_id = current_setting('app.user_id', true)::uuid);

-- Policy: Immutability - Prevent updates to execution logs
-- Ensures audit trail cannot be tampered with
CREATE POLICY execution_logs_immutable ON execution_logs
FOR UPDATE
USING (false);

-- Policy: Immutability - Prevent deletes from execution logs
CREATE POLICY execution_logs_immutable_delete ON execution_logs
FOR DELETE
USING (false);

-- =============================================================================
-- COMPLIANCE ROLE (OPTIONAL)
-- =============================================================================

-- If compliance_auditor role exists, grant SELECT on all logs
-- Uncomment and create role if needed:
-- CREATE ROLE compliance_auditor;
-- GRANT SELECT ON execution_logs TO compliance_auditor;
-- ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT SELECT ON execution_logs TO compliance_auditor;

-- =============================================================================
-- TESTING RLS POLICIES
-- =============================================================================

-- Test trader isolation (replace UUID with test trader ID):
-- SET app.user_id = 'test-trader-uuid-here';
-- SELECT * FROM orders;  -- Should only see orders for test-trader-uuid-here
-- RESET app.user_id;

-- Test immutability:
-- UPDATE execution_logs SET reason = 'modified' WHERE id = 'some-id';
-- Expected: Policy violation error

-- =============================================================================
-- ROLLBACK
-- =============================================================================

-- To remove all policies:
-- DROP POLICY IF EXISTS execution_logs_immutable_delete ON execution_logs;
-- DROP POLICY IF EXISTS execution_logs_immutable ON execution_logs;
-- DROP POLICY IF EXISTS execution_logs_trader_isolation ON execution_logs;
-- DROP POLICY IF EXISTS fills_trader_isolation ON fills;
-- DROP POLICY IF EXISTS orders_trader_isolation ON orders;
--
-- ALTER TABLE execution_logs DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE fills DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders DISABLE ROW LEVEL SECURITY;
