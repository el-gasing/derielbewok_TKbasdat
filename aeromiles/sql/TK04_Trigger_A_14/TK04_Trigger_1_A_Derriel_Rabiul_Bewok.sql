
-- TRIGGER 1: Email Duplication Check on Registration

CREATE OR REPLACE FUNCTION fn_check_duplicate_email()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if email already exists (case-insensitive)
    IF EXISTS (
        SELECT 1 FROM auth_user
        WHERE LOWER(email) = LOWER(NEW.email)
          AND id != COALESCE(NEW.id, 0)
    ) THEN
        RAISE EXCEPTION 'ERROR: Email "%" sudah terdaftar, silakan gunakan email lain.', NEW.email;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER TR_CHECK_DUPLICATE_EMAIL
BEFORE INSERT OR UPDATE ON auth_user
FOR EACH ROW
EXECUTE FUNCTION fn_check_duplicate_email();

-- TRIGGER 2: Login Credential Verification

CREATE OR REPLACE FUNCTION sp_verify_login_credentials(
    p_email VARCHAR,
    p_password VARCHAR
)
RETURNS TABLE (
    user_id BIGINT,
    username VARCHAR,
    email VARCHAR,
    is_active BOOLEAN,
    is_staff BOOLEAN,
    login_status VARCHAR
) AS $$
BEGIN
    -- Check 1: Email exists
    IF NOT EXISTS (SELECT 1 FROM auth_user WHERE LOWER(email) = LOWER(p_email)) THEN
        RETURN QUERY SELECT 
            0::BIGINT,
            ''::VARCHAR,
            p_email::VARCHAR,
            FALSE::BOOLEAN,
            FALSE::BOOLEAN,
            'ERROR: Email atau password salah, silakan coba lagi.'::VARCHAR;
        RETURN;
    END IF;

    RETURN QUERY SELECT 
        u.id,
        u.username,
        u.email,
        u.is_active,
        (SELECT COUNT(*) > 0 FROM auth_system_staff WHERE user_id = u.id)::BOOLEAN,
        'PENDING'::VARCHAR
    FROM auth_user u
    WHERE LOWER(u.email) = LOWER(p_email)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
