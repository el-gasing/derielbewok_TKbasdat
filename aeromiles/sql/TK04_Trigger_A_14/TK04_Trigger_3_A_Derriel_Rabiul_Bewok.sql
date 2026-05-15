-- Create Function 1. Validasi dan Update Saldo Award Miles saat Redeem Hadiah 
DROP TRIGGER IF EXISTS TR_VALIDATE_REDEEM_HADIAH ON auth_system_redeem;
DROP FUNCTION IF EXISTS fn_validate_and_update_redeem();

CREATE OR REPLACE FUNCTION fn_validate_and_update_redeem()
RETURNS TRIGGER AS $$
DECLARE
    v_award_miles BIGINT;
    v_miles_diperlukan BIGINT;
    v_nama_hadiah VARCHAR;
    v_tanggal_mulai DATE;
    v_tanggal_akhir DATE;
    v_sekarang DATE := CURRENT_DATE;
BEGIN

    SELECT award_miles INTO v_award_miles
    FROM auth_system_member
    WHERE id = NEW.member_id;

    SELECT nama_hadiah, miles_diperlukan, tanggal_valid_mulai, tanggal_valid_akhir 
    INTO v_nama_hadiah, v_miles_diperlukan, v_tanggal_mulai, v_tanggal_akhir
    FROM auth_system_hadiah
    WHERE id = NEW.hadiah_id;

    IF v_sekarang < v_tanggal_mulai OR v_sekarang > v_tanggal_akhir THEN
        RAISE EXCEPTION 'ERROR: Hadiah "%" tidak tersedia pada periode ini.', v_nama_hadiah;
    END IF;

    IF v_award_miles < v_miles_diperlukan THEN
        RAISE EXCEPTION 'ERROR: Saldo award miles tidak mencukupi. Dibutuhkan % miles, saldo Anda: % miles.', v_miles_diperlukan, v_award_miles;
    END IF;

    NEW.miles_used := v_miles_diperlukan;

    UPDATE auth_system_member
    SET award_miles = award_miles - v_miles_diperlukan
    WHERE id = NEW.member_id;

    UPDATE auth_system_hadiah
    SET jumlah_terjual = jumlah_terjual + 1
    WHERE id = NEW.hadiah_id;

    RAISE NOTICE 'SUKSES: Redeem hadiah "%" berhasil. Award miles Anda berkurang % miles.', v_nama_hadiah, v_miles_diperlukan;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create Trigger 1. Validasi dan Update Saldo Award Miles saat Redeem Hadiah 
CREATE TRIGGER TR_VALIDATE_REDEEM_HADIAH
BEFORE INSERT ON auth_system_redeem
FOR EACH ROW
EXECUTE FUNCTION fn_validate_and_update_redeem();

-- Create Function 2. Sinkronisasi Award Miles setelah Transaksi Pembelian Package
DROP TRIGGER IF EXISTS TR_SYNC_PEMBELIAN_PACKAGE ON auth_system_memberawardmilespackage;
DROP FUNCTION IF EXISTS fn_sync_miles_pembelian_package();

CREATE OR REPLACE FUNCTION fn_sync_miles_pembelian_package()
RETURNS TRIGGER AS $$
DECLARE
    v_jumlah_award_miles BIGINT;
BEGIN

    SELECT jumlah_award_miles INTO v_jumlah_award_miles
    FROM auth_system_awardmilespackage
    WHERE id = NEW.award_miles_package_id;

    UPDATE auth_system_member
    SET award_miles = award_miles + v_jumlah_award_miles,
        total_miles = total_miles + v_jumlah_award_miles
    WHERE id = NEW.member_id;

    RAISE NOTICE 'SUKSES: Pembelian package berhasil. Award miles dan total miles Anda bertambah % miles.', v_jumlah_award_miles;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create Trigger 2. Sinkronisasi Award Miles setelah Transaksi Pembelian Package
CREATE TRIGGER TR_SYNC_PEMBELIAN_PACKAGE
AFTER INSERT ON auth_system_memberawardmilespackage
FOR EACH ROW
EXECUTE FUNCTION fn_sync_miles_pembelian_package();