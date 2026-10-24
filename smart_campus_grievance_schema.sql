-- Smart Campus Complaint & Grievance Management System
-- PostgreSQL starter schema. Review and run through migrations in a real project.

CREATE TABLE departments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role VARCHAR(20) NOT NULL CHECK
    (role IN ('student','staff','officer','admin')),
  department_id BIGINT REFERENCES departments(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE categories (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  default_department_id BIGINT REFERENCES departments(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE complaints (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ticket_id VARCHAR(32) UNIQUE,
  reporter_id BIGINT NOT NULL REFERENCES users(id),
  category_id BIGINT NOT NULL REFERENCES categories(id),
  department_id BIGINT REFERENCES departments(id),
  assigned_to BIGINT REFERENCES users(id),
  title VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  location VARCHAR(200) NOT NULL,
  image_key TEXT,
  priority VARCHAR(20) NOT NULL DEFAULT 'Normal'
    CHECK (priority IN ('Low','Normal','High','Urgent')),
  status VARCHAR(20) NOT NULL DEFAULT 'Submitted'
    CHECK (status IN ('Submitted','In Progress','Resolved','Rejected')),
  rejection_reason TEXT,
  resolution_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  CHECK (status <> 'Rejected' OR rejection_reason IS NOT NULL),
  CHECK (status <> 'Resolved' OR resolved_at IS NOT NULL)
);

CREATE TABLE complaint_history (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  complaint_id BIGINT NOT NULL REFERENCES complaints(id),
  actor_id BIGINT NOT NULL REFERENCES users(id),
  action VARCHAR(40) NOT NULL,
  old_status VARCHAR(20),
  new_status VARCHAR(20),
  remarks TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE feedback (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  complaint_id BIGINT NOT NULL UNIQUE REFERENCES complaints(id),
  rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comments TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_complaints_reporter_created
  ON complaints(reporter_id, created_at DESC);
CREATE INDEX idx_complaints_department_status
  ON complaints(department_id, status);
CREATE INDEX idx_complaints_assigned_to
  ON complaints(assigned_to);
CREATE INDEX idx_complaint_history_ticket
  ON complaint_history(complaint_id, created_at);
