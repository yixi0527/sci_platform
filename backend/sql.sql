CREATE DATABASE IF NOT EXISTS `sci_platform` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sci_platform;

SET FOREIGN_KEY_CHECKS = 0;

SET @tables = NULL;
SELECT GROUP_CONCAT('`', table_name, '`') INTO @tables
FROM information_schema.tables 
WHERE table_schema = (SELECT DATABASE());

SET @sql = IFNULL(CONCAT('DROP TABLE ', @tables), 'SELECT "No tables to drop"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET FOREIGN_KEY_CHECKS = 1;

----------------------------------------------
CREATE TABLE User (
    userId INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    passwordHash VARCHAR(255) NOT NULL,
    roles VARCHAR(500) NOT NULL DEFAULT '["researcher"]',
    realName VARCHAR(100),
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建admin用户
INSERT INTO User (username, passwordHash, roles, realName) VALUES 
('admin', '$2b$12$N2qtyLglF22jAKqFW.bZze9UlFAWYYOSP09k29Bps/g4viM6DssTK', '["admin"]', 'wtq');
----------------------------------------------
----------------------------------------------

CREATE TABLE Tag (
    tagId INT PRIMARY KEY AUTO_INCREMENT,
    tagName VARCHAR(100) NOT NULL,
    tagDescription VARCHAR(255),
    entityType ENUM('PROJECT', 'SUBJECT', 'USER', 'DATAITEM') NOT NULL COMMENT '标签所属实体类型',
    userId INT NULL COMMENT '创建此标签的用户ID',
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES User(userId) ON DELETE SET NULL,
    INDEX idx_entity_type (entityType),
    INDEX idx_user (userId),
    UNIQUE KEY uk_tag_name_entity_user (tagName, entityType, userId) COMMENT '同一用户对同一实体类型的标签名不能重复'
);

CREATE TABLE Project (
    projectId INT PRIMARY KEY AUTO_INCREMENT,
    projectName VARCHAR(255) UNIQUE NOT NULL,
    tagIds JSON NULL COMMENT '关联的标签ID列表',
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE UserProject (
    userProjectId INT PRIMARY KEY AUTO_INCREMENT,
    userId INT NOT NULL,
    projectId INT NOT NULL,
    FOREIGN KEY (userId) REFERENCES User(userId) ON DELETE CASCADE,
    FOREIGN KEY (projectId) REFERENCES Project(projectId) ON DELETE CASCADE,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

----------------------------------------------

CREATE TABLE Subject (
    subjectId INT PRIMARY KEY AUTO_INCREMENT,
    subjectName VARCHAR(50) NOT NULL,
    tagIds JSON NULL COMMENT '关联的标签ID列表',
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

----------------------------------------------

CREATE TABLE DataItem (
    dataItemId INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '数据项名称',
    userId INT NULL COMMENT '创建者用户ID',
    projectId INT NOT NULL COMMENT '关联项目ID',
    subjectId INT COMMENT '关联受试者ID（可为空：分析结果文件不一定属于某个subject）',
    tagIds JSON NULL COMMENT '关联的标签ID列表',
    fileDescription TEXT COMMENT '文件描述',
    -- file metadata
    filePath VARCHAR(500) COMMENT '文件在服务器上的相对路径',
    fileName VARCHAR(255) COMMENT '原始文件名',
    fileType VARCHAR(50) COMMENT '文件类型/扩展名（如 edf, csv, json）',
    dataType VARCHAR(50) COMMENT '数据类别：raw(原始), processed(处理后), result(结果)',
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (projectId) REFERENCES Project(projectId) ON DELETE CASCADE,
    FOREIGN KEY (subjectId) REFERENCES Subject(subjectId) ON DELETE SET NULL,
    FOREIGN KEY (userId) REFERENCES User(userId) ON DELETE SET NULL,
    INDEX idx_project (projectId),
    INDEX idx_subject (subjectId),
    INDEX idx_user (userId),
    INDEX idx_data_type (dataType)
);


----------------------------------------------

CREATE TABLE LogEntry (
    logId INT PRIMARY KEY AUTO_INCREMENT,
    userId INT NULL,
    action VARCHAR(100),
    detail JSON,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userId) REFERENCES User(userId) ON DELETE SET NULL
);

-- ----------------------------------------------
-- 插入模拟数据 (示例数据用于开发/测试)
-- ----------------------------------------------

-- Users (示例用户)
INSERT INTO User (username, passwordHash, roles, realName) VALUES
('alice', '$2b$12$examplehashalice................................', '["researcher"]', 'Alice Zhang'),
('bob',   '$2b$12$examplehashbob................................',   '["researcher"]', 'Bob Li'),
('carol', '$2b$12$examplehashcarol..............................', '["maintainer"]', 'Carol Wang');

-- Projects
INSERT INTO Project (projectName) VALUES
('SleepStudy'),
('MemoryTask'),
('EEG_Analysis');

-- Link users to projects
INSERT INTO UserProject (userId, projectId) VALUES
(1, 1), -- admin -> SleepStudy
(2, 1), -- alice -> SleepStudy
(3, 2), -- bob -> MemoryTask
(4, 3); -- carol -> EEG_Analysis

-- Subjects
INSERT INTO Subject (subjectName) VALUES
('S001'),
('S002'),
('S003');

-- Tags (示例数据，不同实体类型的标签)
INSERT INTO Tag (tagName, tagDescription, entityType, userId) VALUES
('高质量', '数据质量良好', 'DataItem', 1),
('存在伪迹', '存在明显伪迹或噪声', 'DataItem', 1),
('已处理', '分析/处理后文件', 'DataItem', 2),
('重要项目', '优先级高的项目', 'Project', 1),
('实验组', '实验组受试者', 'Subject', 1),
('对照组', '对照组受试者', 'Subject', 1);

-- DataItem (示例文件条目)
INSERT INTO DataItem (name, userId, projectId, subjectId, fileDescription, filePath, fileName, fileType, dataType) VALUES
('S001_session1_raw', 2, 1, 1, '原始采集文件，通道32', '/data/SleepStudy/S001/session1_raw.edf', 'S001_session1_raw.edf', 'edf', 'raw'),
('S001_session1_clean', 3, 1, 1, '经清理后数据（去伪迹）', '/data/SleepStudy/S001/session1_clean.set', 'S001_session1_clean.set', 'set', 'processed'),
('S002_session2_raw', 3, 1, 2, '原始采集文件，通道32', '/data/SleepStudy/S002/session2_raw.edf', 'S002_session2_raw.edf', 'edf', 'raw'),
('memory_task_subj3_raw', 4, 2, 3, '记忆任务原始数据', '/data/MemoryTask/S003/session1.vhdr', 'memory_task_subj3_raw.vhdr', 'vhdr', 'raw'),
('eeg_analysis_result_01', 1, 3, NULL, '自动化分析结果（不属于具体受试者）', '/results/EEG_Analysis/result_01.json', 'eeg_analysis_result_01.json', 'json', 'result');

-- LogEntry
INSERT INTO LogEntry (userId, action, detail) VALUES
(1, 'create_project', JSON_OBJECT('projectName', 'SleepStudy')),
(2, 'upload_file', JSON_OBJECT('fileName', 'S001_session1_raw.edf', 'projectId', 1, 'subjectId', 1)),
(1, 'create_tag', JSON_OBJECT('tagName', '高质量', 'entityType', 'DataItem'));

-- ----------------------------------------------
-- 完成