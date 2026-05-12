-- TK04 Trigger 4 - Pemeriksaan Status Klaim Missing Miles Duplikat

DROP TRIGGER IF EXISTS TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS ON auth_system_claimmissingmiles;
DROP FUNCTION IF EXISTS fn_check_duplicate_missing_miles_claims();
DROP FUNCTION IF EXISTS sp_check_duplicate_missing_miles_claim(BIGINT, VARCHAR, VARCHAR, VARCHAR, DATE);

-- Stored Procedure: Check Duplicate Missing Miles Claim
CREATE OR REPLACE FUNCTION sp_check_duplicate_missing_miles_claim(
    p_member_id BIGINT,
    p_email_member VARCHAR,
    p_flight_number VARCHAR,
    p_ticket_number VARCHAR,
    p_flight_date DATE
)
RETURNS BIGINT AS $$
DECLARE
    v_claim_id BIGINT;
BEGIN
    SELECT c.id INTO v_claim_id
    FROM auth_system_claimmissingmiles c
    JOIN auth_system_member m ON m.id = c.member_id
    JOIN auth_user u ON u.id = m.user_id
    WHERE LOWER(u.email) = LOWER(p_email_member)
      AND UPPER(c.flight_number) = UPPER(p_flight_number)
      AND c.flight_date = p_flight_date
      AND COALESCE(UPPER(c.ticket_number), '') = COALESCE(UPPER(p_ticket_number), '')
    LIMIT 1;

    RETURN v_claim_id;
END;
$$ LANGUAGE plpgsql;


-- Trigger Function: Prevent Duplicate Claim Insert/Update
CREATE OR REPLACE FUNCTION fn_check_duplicate_missing_miles_claims()
RETURNS TRIGGER AS $$
DECLARE
    v_member_email TEXT;
BEGIN
    SELECT LOWER(au.email)
    INTO v_member_email
    FROM auth_system_member am
    JOIN auth_user au ON au.id = am.user_id
    WHERE am.id = NEW.member_id;

    IF EXISTS (
        SELECT 1
        FROM auth_system_claimmissingmiles c
        JOIN auth_system_member m ON m.id = c.member_id
        JOIN auth_user u ON u.id = m.user_id
        WHERE UPPER(c.flight_number) = UPPER(NEW.flight_number)
          AND c.flight_date = NEW.flight_date
          AND COALESCE(UPPER(c.ticket_number), '') = COALESCE(UPPER(NEW.ticket_number), '')
          AND LOWER(u.email) = v_member_email
          AND c.id != COALESCE(NEW.id, 0)
    ) THEN
        RAISE EXCEPTION 'ERROR: Klaim untuk penerbangan "%" pada tanggal "%" dengan nomor tiket "%" sudah pernah diajukan sebelumnya.',
            NEW.flight_number, NEW.flight_date, NEW.ticket_number;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- Trigger: TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS
-- ============================================================================
CREATE TRIGGER TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS
BEFORE INSERT OR UPDATE ON auth_system_claimmissingmiles
FOR EACH ROW
EXECUTE FUNCTION fn_check_duplicate_missing_miles_claims();
