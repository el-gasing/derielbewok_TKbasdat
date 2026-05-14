DROP TRIGGER IF EXISTS TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS ON auth_system_claimmissingmiles;
DROP FUNCTION IF EXISTS fn_check_duplicate_missing_miles_claims();
DROP FUNCTION IF EXISTS sp_check_duplicate_missing_miles_claim(BIGINT, VARCHAR, VARCHAR, VARCHAR, DATE);

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


CREATE TRIGGER TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS
BEFORE INSERT OR UPDATE ON auth_system_claimmissingmiles
FOR EACH ROW
EXECUTE FUNCTION fn_check_duplicate_missing_miles_claims();


DROP TRIGGER IF EXISTS TR_AUTO_UPDATE_MEMBER_TIER ON auth_system_member;
DROP FUNCTION IF EXISTS fn_auto_update_member_tier();

CREATE OR REPLACE FUNCTION fn_auto_update_member_tier()
RETURNS TRIGGER AS $$
DECLARE
    v_new_tier_id BIGINT;
    v_old_tier_name TEXT;
    v_new_tier_name TEXT;
    v_email TEXT;
BEGIN
    IF NEW.total_miles = OLD.total_miles THEN
        RETURN NEW;
    END IF;

    SELECT id INTO v_new_tier_id
    FROM auth_system_tier
    WHERE is_active = TRUE
      AND minimal_tier_miles <= NEW.total_miles
    ORDER BY minimal_tier_miles DESC
    LIMIT 1;

    IF v_new_tier_id IS NOT NULL AND v_new_tier_id IS DISTINCT FROM OLD.tier_id THEN
        SELECT tier_name INTO v_old_tier_name
        FROM auth_system_tier
        WHERE id = OLD.tier_id;

        SELECT tier_name INTO v_new_tier_name
        FROM auth_system_tier
        WHERE id = v_new_tier_id;

        SELECT email INTO v_email
        FROM auth_user
        WHERE id = NEW.user_id;

        NEW.tier_id := v_new_tier_id;

        RAISE NOTICE 'SUKSES: Tier Member "%" telah diperbarui dari "%" menjadi "%" berdasarkan total miles yang dimiliki.',
            v_email, COALESCE(v_old_tier_name, 'Tidak Ada'), v_new_tier_name;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER TR_AUTO_UPDATE_MEMBER_TIER
BEFORE UPDATE ON auth_system_member
FOR EACH ROW
EXECUTE FUNCTION fn_auto_update_member_tier();
