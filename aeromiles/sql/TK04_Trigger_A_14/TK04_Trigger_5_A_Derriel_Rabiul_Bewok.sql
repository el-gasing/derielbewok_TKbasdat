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
