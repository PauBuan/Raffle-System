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
    AllocatedPrizes INT          NOT NULL DEFAULT 0
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

-- Sample employees
INSERT INTO _Employees (EmpNo, EmpName, Department) VALUES
('EMP001', 'Juan dela Cruz',       'Engineering'),
('EMP002', 'Maria Santos',         'Engineering'),
('EMP003', 'Pedro Reyes',          'Engineering'),
('EMP004', 'Ana Gonzalez',         'HR'),
('EMP005', 'Jose Ramos',           'HR'),
('EMP006', 'Luz Fernandez',        'HR'),
('EMP007', 'Carlos Villanueva',    'Finance'),
('EMP008', 'Elena Torres',         'Finance'),
('EMP009', 'Roberto Aquino',       'Finance'),
('EMP010', 'Maricel Bautista',     'Marketing'),
('EMP011', 'Andres Castillo',      'Marketing'),
('EMP012', 'Cristina Lim',         'Marketing'),
('OJT26A01', 'OJT Intern Alpha',   'Engineering'),
('OJT26A02', 'OJT Intern Beta',    'Engineering'),
('OJT26A03', 'OJT Intern Gamma',   'HR');

-- Sample prizes
INSERT INTO _Prizes (CategoryID, PrizeName, WinnerCount) VALUES
(1, 'Gift Card P500',    5),
(1, 'Consolation Pack',  3),
(2, 'Smart TV 32"',      2),
(2, 'Air Fryer',         1),
(3, 'Laptop',            1),
(3, 'Motorcycle',        1);
