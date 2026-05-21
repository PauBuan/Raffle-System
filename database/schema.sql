-- ============================================================
-- Raffle System Database Schema
-- Target: SQL Server 2019 (SQL19)
-- ============================================================

-- ----------------------------------------------------------------
-- Table: Employees
-- Stores employee master data used as raffle participants.
-- ----------------------------------------------------------------
CREATE TABLE Employees (
    EmpNo       VARCHAR(20)  NOT NULL PRIMARY KEY,
    EmpName     VARCHAR(100) NOT NULL,
    Department  VARCHAR(100) NOT NULL
);

-- ----------------------------------------------------------------
-- Table: PrizeCategories
-- Defines the three prize tiers: Minor, Major, Grand.
-- ----------------------------------------------------------------
CREATE TABLE PrizeCategories (
    CategoryID   INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    CategoryName VARCHAR(20)  NOT NULL  -- 'Minor' | 'Major' | 'Grand'
);

-- ----------------------------------------------------------------
-- Table: Prizes
-- Each row is one prize slot within a category.
-- The Quantity column determines how many winners are drawn.
-- ----------------------------------------------------------------
CREATE TABLE Prizes (
    PrizeID      INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    CategoryID   INT          NOT NULL REFERENCES PrizeCategories(CategoryID),
    PrizeName    VARCHAR(200) NOT NULL,
    Quantity     INT          NOT NULL DEFAULT 1,  -- winners per draw
    IsActive     BIT          NOT NULL DEFAULT 1
);

-- ----------------------------------------------------------------
-- Table: RaffleWinners
-- Records every drawn winner.  IsRedraw flags replacement draws.
-- ----------------------------------------------------------------
CREATE TABLE RaffleWinners (
    WinnerID    INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    PrizeID     INT          NOT NULL REFERENCES Prizes(PrizeID),
    EmpNo       VARCHAR(20)  NOT NULL REFERENCES Employees(EmpNo),
    Department  VARCHAR(100) NOT NULL,
    DrawnAt     DATETIME     NOT NULL DEFAULT GETDATE(),
    IsRedraw    BIT          NOT NULL DEFAULT 0
);

-- ----------------------------------------------------------------
-- Table: RaffleSession
-- Tracks the active session / event.
-- ----------------------------------------------------------------
CREATE TABLE RaffleSession (
    SessionID   INT          NOT NULL PRIMARY KEY IDENTITY(1,1),
    SessionName VARCHAR(200) NOT NULL,
    Department  VARCHAR(100) NOT NULL,  -- department in scope for this draw
    CreatedAt   DATETIME     NOT NULL DEFAULT GETDATE(),
    IsActive    BIT          NOT NULL DEFAULT 1
);

-- ============================================================
-- Seed Data
-- ============================================================

-- Prize categories (fixed)
INSERT INTO PrizeCategories (CategoryName) VALUES ('Minor');
INSERT INTO PrizeCategories (CategoryName) VALUES ('Major');
INSERT INTO PrizeCategories (CategoryName) VALUES ('Grand');

-- Sample employees
INSERT INTO Employees (EmpNo, EmpName, Department) VALUES
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
INSERT INTO Prizes (CategoryID, PrizeName, Quantity) VALUES
(1, 'Gift Card P500',    5),  -- Minor: 5 winners
(1, 'Consolation Pack',  3),  -- Minor: 3 winners
(2, 'Smart TV 32"',      2),  -- Major: 2 winners
(2, 'Air Fryer',         1),  -- Major: 1 winner
(3, 'Laptop',            1),  -- Grand: 1 winner (unique, no repeats)
(3, 'Motorcycle',        1);  -- Grand: 1 winner (unique, no repeats)
