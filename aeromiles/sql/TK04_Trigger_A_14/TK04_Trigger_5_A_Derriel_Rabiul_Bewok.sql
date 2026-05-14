DROP TRIGGER IF EXISTS TR_SYNC_MILES_ON_CLAIM_APPROVED ON auth_system_claimmissingmiles;
DROP FUNCTION IF EXISTS fn_sync_miles_on_claim_approved();

CREATE OR REPLACE FUNCTION fn_sync_miles_on_claim_approved()
RETURNS TRIGGER AS $$
DECLARE
    v_email TEXT;
BEGIN
    IF NEW.status = 'approved' AND (OLD.status IS NULL OR OLD.status <> 'approved') THEN
        UPDATE auth_system_member
        SET award_miles = award_miles + 1000,
            total_miles = total_miles + 1000,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.member_id;

        SELECT u.email INTO v_email
        FROM auth_user u
        JOIN auth_system_member m ON m.user_id = u.id
        WHERE m.id = NEW.member_id;

        RAISE NOTICE 'SUKSES: Total miles Member "%" telah diperbarui. Miles ditambahkan: 1000 miles dari klaim penerbangan "%".',
            v_email, NEW.flight_number;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER TR_SYNC_MILES_ON_CLAIM_APPROVED
AFTER UPDATE ON auth_system_claimmissingmiles
FOR EACH ROW
EXECUTE FUNCTION fn_sync_miles_on_claim_approved();


DROP FUNCTION IF EXISTS sp_get_top_5_members();

CREATE OR REPLACE FUNCTION sp_get_top_5_members()
RETURNS TABLE (
    rank_no INTEGER,
    member_email VARCHAR,
    member_name TEXT,
    total_miles BIGINT
) AS $$
DECLARE
    v_top_email VARCHAR;
    v_top_miles BIGINT;
BEGIN
    RETURN QUERY
    SELECT
        ROW_NUMBER() OVER (ORDER BY m.total_miles DESC, u.email ASC)::INTEGER AS rank_no,
        u.email::VARCHAR AS member_email,
        TRIM(CONCAT(u.first_name, ' ', u.last_name)) AS member_name,
        m.total_miles
    FROM auth_system_member m
    JOIN auth_user u ON u.id = m.user_id
    WHERE m.is_active = TRUE
    ORDER BY m.total_miles DESC, u.email ASC
    LIMIT 5;

    SELECT u.email, m.total_miles
    INTO v_top_email, v_top_miles
    FROM auth_system_member m
    JOIN auth_user u ON u.id = m.user_id
    WHERE m.is_active = TRUE
    ORDER BY m.total_miles DESC, u.email ASC
    LIMIT 1;

    IF v_top_email IS NOT NULL THEN
        RAISE NOTICE 'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, dengan peringkat pertama "%" memiliki % miles.',
            v_top_email, v_top_miles;
    END IF;
END;
$$ LANGUAGE plpgsql;
