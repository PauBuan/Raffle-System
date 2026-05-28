-- ============================================================
-- Migration 004: Add Status column to _Groups
-- Raffle System v3.0.0
-- ============================================================

ALTER TABLE _Groups
ADD Status NVARCHAR(20) NOT NULL DEFAULT 'NOT SET';

ALTER TABLE _Groups
ADD CONSTRAINT CHK_GroupStatus CHECK (Status IN ('NOT SET', 'READY FOR DRAWING'));
