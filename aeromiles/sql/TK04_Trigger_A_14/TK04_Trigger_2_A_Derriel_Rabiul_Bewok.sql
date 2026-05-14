-- TRIGGER 2: Pencegahan Transfer Miles Melebihi Saldo dan Pencatatan Riwayat

DROP TRIGGER IF EXISTS TR_TRANSFER_MILES_CHECK ON auth_system_transfermiles;
DROP FUNCTION IF EXISTS fn_transfer_miles_check();

CREATE OR REPLACE FUNCTION fn_transfer_miles_check()
RETURNS TRIGGER AS $$
DECLARE
    v_pengirim_email TEXT;
    v_penerima_email TEXT;
    v_pengirim_award_miles BIGINT;
BEGIN
    -- 1. Mendapatkan email pengirim dan saldo award_miles
    SELECT u.email, m.award_miles INTO v_pengirim_email, v_pengirim_award_miles
    FROM auth_system_member m
    JOIN auth_user u ON u.id = m.user_id
    WHERE m.id = NEW.from_member_id;

    -- 2. Mendapatkan email penerima
    SELECT u.email INTO v_penerima_email
    FROM auth_system_member m
    JOIN auth_user u ON u.id = m.user_id
    WHERE m.id = NEW.to_member_id;

    -- 3. Pencegahan Transfer Miles Melebihi Saldo
    IF NEW.miles_amount > v_pengirim_award_miles THEN
        RAISE EXCEPTION 'ERROR: Saldo award miles tidak mencukupi. Saldo Anda saat ini: % miles, jumlah transfer: % miles.',
            v_pengirim_award_miles, NEW.miles_amount;
    END IF;

    -- 4. Pencatatan Log Riwayat Transfer Miles (Pembaruan saldo pengirim dan penerima)
    -- Jumlah award_miles pengirim akan berkurang
    UPDATE auth_system_member
    SET award_miles = award_miles - NEW.miles_amount,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.from_member_id;

    -- Jumlah award_miles dan total_miles penerima akan bertambah
    UPDATE auth_system_member
    SET award_miles = award_miles + NEW.miles_amount,
        total_miles = total_miles + NEW.miles_amount,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.to_member_id;

    -- Tampilkan pesan SUKSES
    RAISE NOTICE 'SUKSES: Transfer % miles dari "%" ke "%" berhasil dicatat.',
        NEW.miles_amount, v_pengirim_email, v_penerima_email;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER TR_TRANSFER_MILES_CHECK
BEFORE INSERT ON auth_system_transfermiles
FOR EACH ROW
EXECUTE FUNCTION fn_transfer_miles_check();
