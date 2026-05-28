-- ============================================================
-- Migration 003: Add Building column to _Employees
-- Raffle System v3.0.0
-- ============================================================

ALTER TABLE _Employees
ADD Building NVARCHAR(10) NOT NULL DEFAULT 'LTI';

ALTER TABLE _Employees
ADD CONSTRAINT CHK_Building CHECK (Building IN ('LTI', 'CIP'));

-- NOTE: All existing employees default to 'LTI'.
-- Admin must manually update CIP employees via admin panel or:
-- UPDATE _Employees SET Building = 'CIP' WHERE Department IN ('...');
