-- ============================================================
-- Raffle System Database Schema v2.0
-- Target: SQL Server 2019 (SQL19)
-- All tables use underscore-prefixed names.
-- ============================================================

-- ----------------------------------------------------------------
-- Table: _Employees
-- ----------------------------------------------------------------
CREATE TABLE _Employees (
    EmpNo                VARCHAR(20)  NOT NULL PRIMARY KEY,
    EmpName              VARCHAR(100) NOT NULL,
    Department           VARCHAR(100) NOT NULL,
    Building             NVARCHAR(10) NOT NULL DEFAULT 'LTI'
                         CONSTRAINT CHK_Building CHECK (Building IN ('LTI', 'CIP')),
    WinChanceMultiplier  INT          NOT NULL DEFAULT 1
);

-- ----------------------------------------------------------------
-- Table: _PrizeCategories
-- ----------------------------------------------------------------
CREATE TABLE _PrizeCategories (
    CategoryID   INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    CategoryName VARCHAR(50)  NOT NULL
);

-- ----------------------------------------------------------------
-- Table: _Prizes
-- ----------------------------------------------------------------
CREATE TABLE _Prizes (
    PrizeID      INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    CategoryID   INT          NOT NULL REFERENCES _PrizeCategories(CategoryID),
    PrizeName    VARCHAR(200) NOT NULL,
    WinnerCount  INT          NOT NULL DEFAULT 1,
    IsActive     BIT          NOT NULL DEFAULT 1
);

-- ----------------------------------------------------------------
-- Table: _Events
-- (Created before _RaffleWinners because of FK dependency)
-- ----------------------------------------------------------------
CREATE TABLE _Events (
    EventID    INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    EventName  VARCHAR(150) NOT NULL,
    CreatedAt  DATETIME     NOT NULL DEFAULT GETDATE(),
    IsActive   BIT          NOT NULL DEFAULT 1
);

-- ----------------------------------------------------------------
-- Table: _RaffleWinners
-- ----------------------------------------------------------------
CREATE TABLE _RaffleWinners (
    WinnerID    INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    PrizeID     INT          NOT NULL REFERENCES _Prizes(PrizeID),
    EmpNo       VARCHAR(20)  NOT NULL REFERENCES _Employees(EmpNo),
    Department  VARCHAR(100) NOT NULL,
    DrawnAt     DATETIME     NOT NULL DEFAULT GETDATE(),
    IsRedraw    BIT          NOT NULL DEFAULT 0,
    IsConfirmed BIT          NOT NULL DEFAULT 0,
    EventID     INT          NULL     REFERENCES _Events(EventID)
);

-- ----------------------------------------------------------------
-- Table: _Groups
-- ----------------------------------------------------------------
CREATE TABLE _Groups (
    GroupID         INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    GroupName       VARCHAR(100) NOT NULL,
    BuildingTag     VARCHAR(10)  NULL,      -- 'LTI' | 'CIP' | NULL
    AllocatedPrizes INT          NOT NULL DEFAULT 0,
    Status          NVARCHAR(20) NOT NULL DEFAULT 'NOT SET'
                    CONSTRAINT CHK_GroupStatus CHECK (Status IN ('NOT SET', 'READY FOR DRAWING'))
);

-- ----------------------------------------------------------------
-- Table: _GroupDepartments
-- ----------------------------------------------------------------
CREATE TABLE _GroupDepartments (
    ID         INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    GroupID    INT          NOT NULL REFERENCES _Groups(GroupID),
    Department VARCHAR(100) NOT NULL
);

-- ----------------------------------------------------------------
-- Table: _EventParticipants
-- ----------------------------------------------------------------
CREATE TABLE _EventParticipants (
    ID      INT         NOT NULL PRIMARY KEY IDENTITY(1,1),
    EventID INT         NOT NULL REFERENCES _Events(EventID),
    EmpNo   VARCHAR(20) NOT NULL REFERENCES _Employees(EmpNo)
);

-- ----------------------------------------------------------------
-- Table: _AdminAuditLog
-- ----------------------------------------------------------------
CREATE TABLE _AdminAuditLog (
    LogID       INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    AdminName   VARCHAR(100) NOT NULL,
    ChangesMade NVARCHAR(MAX) NOT NULL,
    ChangedAt   DATETIME     NOT NULL DEFAULT GETDATE()
);

-- ----------------------------------------------------------------
-- Table: _DepartmentSettings
-- ----------------------------------------------------------------
CREATE TABLE _DepartmentSettings (
    DeptName              VARCHAR(100) NOT NULL PRIMARY KEY,
    WinChanceMultiplier   INT          NOT NULL DEFAULT 1
);

-- ============================================================
-- Seed Data
-- ============================================================

-- Prize categories (fixed)
INSERT INTO _PrizeCategories (CategoryName) VALUES ('Minor');
INSERT INTO _PrizeCategories (CategoryName) VALUES ('Major');
INSERT INTO _PrizeCategories (CategoryName) VALUES ('Grand');

-- Sample employees (Building: LTI or CIP)
INSERT INTO _Employees (EmpNo, EmpName, Department, Building) VALUES
('EMP001', 'Juan dela Cruz',       'Engineering',  'LTI'),
('EMP002', 'Maria Santos',         'Engineering',  'LTI'),
('EMP003', 'Pedro Reyes',          'Engineering',  'CIP'),
('EMP004', 'Ana Gonzalez',         'HR',           'LTI'),
('EMP005', 'Jose Ramos',           'HR',           'CIP'),
('EMP006', 'Luz Fernandez',        'HR',           'CIP'),
('EMP007', 'Carlos Villanueva',    'Finance',      'LTI'),
('EMP008', 'Elena Torres',         'Finance',      'LTI'),
('EMP009', 'Roberto Aquino',       'Finance',      'CIP'),
('EMP010', 'Maricel Bautista',     'Marketing',    'LTI'),
('EMP011', 'Andres Castillo',      'Marketing',    'CIP'),
('EMP012', 'Cristina Lim',         'Marketing',    'LTI'),
('OJT26A01', 'OJT Intern Alpha',   'Engineering', 'LTI'),
('OJT26A02', 'OJT Intern Beta',    'Engineering', 'LTI'),
('OJT26A03', 'OJT Intern Gamma',   'HR',          'CIP');

-- Sample prizes
INSERT INTO _Prizes (CategoryID, PrizeName, WinnerCount) VALUES
(1, 'Gift Card P500',    5),
(1, 'Consolation Pack',  3),
(2, 'Smart TV 32"',      2),
(2, 'Air Fryer',         1),
(3, 'Laptop',            1),
(3, 'Motorcycle',        1);
