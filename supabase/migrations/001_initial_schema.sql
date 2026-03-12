-- CRM Deduplication Tool - Initial Schema
-- Run this in Supabase SQL Editor or via migrations

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- CRM Connections table
CREATE TABLE crm_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    crm_type TEXT NOT NULL CHECK (crm_type IN ('hubspot', 'salesforce')),
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    portal_id TEXT,  -- HubSpot portal ID or Salesforce org ID
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, crm_type)
);

-- Scans table
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES crm_connections(id) ON DELETE CASCADE,
    object_type TEXT NOT NULL CHECK (object_type IN ('contacts', 'companies', 'deals')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    config JSONB NOT NULL,  -- winner rules, thresholds, etc.
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    records_scanned INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Duplicate Sets table (temporary, for review)
CREATE TABLE duplicate_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    confidence NUMERIC(5,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    winner_record_id TEXT NOT NULL,
    loser_record_ids TEXT[] NOT NULL,
    winner_data JSONB NOT NULL,
    loser_data JSONB NOT NULL,
    merged_preview JSONB NOT NULL,
    excluded BOOLEAN DEFAULT FALSE,
    merged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Merges table
CREATE TABLE merges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'paused')),
    total_sets INTEGER NOT NULL,
    completed_sets INTEGER DEFAULT 0,
    failed_sets INTEGER DEFAULT 0,
    error_log JSONB,  -- Array of {set_id, error}
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reports table
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merge_id UUID NOT NULL REFERENCES merges(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    report_data JSONB NOT NULL,
    pdf_url TEXT,  -- Supabase storage URL
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_scans_user_id ON scans(user_id);
CREATE INDEX idx_scans_status ON scans(status);
CREATE INDEX idx_duplicate_sets_scan_id ON duplicate_sets(scan_id);
CREATE INDEX idx_duplicate_sets_excluded ON duplicate_sets(excluded);
CREATE INDEX idx_merges_scan_id ON merges(scan_id);
CREATE INDEX idx_reports_user_id ON reports(user_id);

-- Row Level Security (RLS)
ALTER TABLE crm_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE merges ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own data
CREATE POLICY "Users can view own connections"
    ON crm_connections FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own connections"
    ON crm_connections FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own connections"
    ON crm_connections FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own connections"
    ON crm_connections FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view own scans"
    ON scans FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own scans"
    ON scans FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view duplicate sets from own scans"
    ON duplicate_sets FOR SELECT
    USING (EXISTS (SELECT 1 FROM scans WHERE scans.id = duplicate_sets.scan_id AND scans.user_id = auth.uid()));

CREATE POLICY "Users can update duplicate sets from own scans"
    ON duplicate_sets FOR UPDATE
    USING (EXISTS (SELECT 1 FROM scans WHERE scans.id = duplicate_sets.scan_id AND scans.user_id = auth.uid()));

CREATE POLICY "Users can view own merges"
    ON merges FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own merges"
    ON merges FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own reports"
    ON reports FOR SELECT
    USING (auth.uid() = user_id);

-- Service role bypass for backend operations
-- Note: Backend uses service_role key which bypasses RLS

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to crm_connections
CREATE TRIGGER update_crm_connections_updated_at
    BEFORE UPDATE ON crm_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
