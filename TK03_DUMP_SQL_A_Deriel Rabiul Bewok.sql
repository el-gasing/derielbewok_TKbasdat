-- 0. Buat Schema
CREATE SCHEMA AEROMILES;
SET search_path TO AEROMILES;

-- 1. Tabel PENGGUNA
CREATE TABLE PENGGUNA (
    email VARCHAR(100) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    salutation VARCHAR(10) NOT NULL,
    first_mid_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    country_code VARCHAR(5) NOT NULL,
    mobile_number VARCHAR(20) NOT NULL,
    tanggal_lahir DATE NOT NULL,
    kewarganegaraan VARCHAR(50) NOT NULL
);

-- 2. Tabel TIER
CREATE TABLE TIER (
    id_tier VARCHAR(10) PRIMARY KEY,
    nama VARCHAR(50) NOT NULL,
    minimal_frekuensi_terbang INT NOT NULL,
    minimal_tier_miles INT NOT NULL
);

-- 3. Tabel MEMBER
CREATE TABLE MEMBER (
    email VARCHAR(100) PRIMARY KEY,
    nomor_member VARCHAR(20) UNIQUE NOT NULL,
    tanggal_bergabung DATE NOT NULL,
    id_tier VARCHAR(10) NOT NULL,
    award_miles INT DEFAULT 0,
    total_miles INT DEFAULT 0,
    CONSTRAINT fk_member_pengguna FOREIGN KEY (email) REFERENCES PENGGUNA(email),
    CONSTRAINT fk_member_tier FOREIGN KEY (id_tier) REFERENCES TIER(id_tier)
);

-- 4. Tabel IDENTITAS
CREATE TABLE IDENTITAS (
    nomor VARCHAR(50) PRIMARY KEY,
    email_member VARCHAR(100) NOT NULL,
    tanggal_habis DATE NOT NULL,
    tanggal_terbit DATE NOT NULL,
    negara_penerbit VARCHAR(50) NOT NULL,
    jenis VARCHAR(30) NOT NULL,
    CONSTRAINT fk_identitas_member FOREIGN KEY (email_member) REFERENCES MEMBER(email) ON DELETE CASCADE
);

-- 5. Tabel PENYEDIA
CREATE TABLE PENYEDIA (
    id SERIAL PRIMARY KEY 
);

-- 6. Tabel MASKAPAI
CREATE TABLE MASKAPAI (
    kode_maskapai VARCHAR(10) PRIMARY KEY,
    nama_maskapai VARCHAR(100) NOT NULL,
    id_penyedia INT NOT NULL,
    CONSTRAINT fk_maskapai_penyedia FOREIGN KEY (id_penyedia) REFERENCES PENYEDIA(id)
);

-- 7. Tabel STAF
CREATE TABLE STAF (
    email VARCHAR(100) PRIMARY KEY,
    id_staf VARCHAR(20) UNIQUE NOT NULL, 
    kode_maskapai VARCHAR(10) NOT NULL,
    CONSTRAINT fk_staf_pengguna FOREIGN KEY (email) REFERENCES PENGGUNA(email),
    CONSTRAINT fk_staf_maskapai FOREIGN KEY (kode_maskapai) REFERENCES MASKAPAI(kode_maskapai)
);

-- 8. Tabel MITRA
CREATE TABLE MITRA (
    email_mitra VARCHAR(100) PRIMARY KEY,
    id_penyedia INT UNIQUE NOT NULL,
    nama_mitra VARCHAR(100) NOT NULL,
    tanggal_kerja_sama DATE NOT NULL,
    CONSTRAINT fk_mitra_penyedia FOREIGN KEY (id_penyedia) REFERENCES PENYEDIA(id) ON DELETE CASCADE
);

-- 9. Tabel AWARD_MILES_PACKAGE
CREATE TABLE AWARD_MILES_PACKAGE (
    id VARCHAR(20) PRIMARY KEY, 
    harga_paket DECIMAL(15,2) NOT NULL,
    jumlah_award_miles INT NOT NULL
);

-- 10. Tabel MEMBER_AWARD_MILES_PACKAGE
CREATE TABLE MEMBER_AWARD_MILES_PACKAGE (
    id_award_miles_package VARCHAR(20) NOT NULL,
    email_member VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (id_award_miles_package, email_member, timestamp),
    CONSTRAINT fk_mamp_package FOREIGN KEY (id_award_miles_package) REFERENCES AWARD_MILES_PACKAGE(id),
    CONSTRAINT fk_mamp_member FOREIGN KEY (email_member) REFERENCES MEMBER(email) ON DELETE CASCADE
);

-- 11. Tabel HADIAH
CREATE TABLE HADIAH (
    kode_hadiah VARCHAR(20) PRIMARY KEY, 
    nama VARCHAR(100) NOT NULL,
    miles INT NOT NULL,
    deskripsi TEXT,
    valid_start_date DATE NOT NULL,
    program_end DATE NOT NULL,
    id_penyedia INT NOT NULL,
    CONSTRAINT fk_hadiah_penyedia FOREIGN KEY (id_penyedia) REFERENCES PENYEDIA(id) ON DELETE CASCADE
);

-- 12. Tabel REDEEM
CREATE TABLE REDEEM (
    email_member VARCHAR(100) NOT NULL,
    kode_hadiah VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (email_member, kode_hadiah, timestamp),
    CONSTRAINT fk_redeem_member FOREIGN KEY (email_member) REFERENCES MEMBER(email) ON DELETE CASCADE,
    CONSTRAINT fk_redeem_hadiah FOREIGN KEY (kode_hadiah) REFERENCES HADIAH(kode_hadiah)
);

-- 13. Tabel BANDARA
CREATE TABLE BANDARA (
    iata_code CHAR(3) PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    kota VARCHAR(100) NOT NULL,
    negara VARCHAR(100) NOT NULL
);

-- 14. Tabel CLAIM_MISSING_MILES
CREATE TABLE CLAIM_MISSING_MILES (
    id SERIAL PRIMARY KEY,
    email_member VARCHAR(100) NOT NULL,
    email_staf VARCHAR(100), 
    maskapai VARCHAR(10) NOT NULL,
    bandara_asal VARCHAR(3) NOT NULL,
    bandara_tujuan VARCHAR(3) NOT NULL,
    tanggal_penerbangan DATE NOT NULL,
    flight_number VARCHAR(10) NOT NULL,
    nomor_tiket VARCHAR(20) NOT NULL,
    kelas_kabin VARCHAR(20) NOT NULL,
    pnr VARCHAR(10) NOT NULL,
    status_penerimaan VARCHAR(20) DEFAULT 'Menunggu' NOT NULL, 
    timestamp TIMESTAMP NOT NULL,
    CONSTRAINT fk_cmm_member FOREIGN KEY (email_member) REFERENCES MEMBER(email) ON DELETE CASCADE,
    CONSTRAINT fk_cmm_staf FOREIGN KEY (email_staf) REFERENCES STAF(email),
    CONSTRAINT fk_cmm_maskapai FOREIGN KEY (maskapai) REFERENCES MASKAPAI(kode_maskapai),
    CONSTRAINT fk_cmm_asal FOREIGN KEY (bandara_asal) REFERENCES BANDARA(iata_code),
    CONSTRAINT fk_cmm_tujuan FOREIGN KEY (bandara_tujuan) REFERENCES BANDARA(iata_code),
    CONSTRAINT unique_klaim UNIQUE (email_member, flight_number, tanggal_penerbangan, nomor_tiket)
);

-- 15. Tabel TRANSFER
CREATE TABLE TRANSFER (
    email_member_1 VARCHAR(100) NOT NULL,
    email_member_2 VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    jumlah INT NOT NULL,
    catatan VARCHAR(255),
    PRIMARY KEY (email_member_1, email_member_2, timestamp),
    CONSTRAINT fk_tf_pengirim FOREIGN KEY (email_member_1) REFERENCES MEMBER(email) ON DELETE CASCADE,
    CONSTRAINT fk_tf_penerima FOREIGN KEY (email_member_2) REFERENCES MEMBER(email) ON DELETE CASCADE,
    CONSTRAINT check_transfer_diri_sendiri CHECK (email_member_1 <> email_member_2)
);


-- Data Dummy

-- 1. TIER (4 Data)
INSERT INTO TIER VALUES 
('T01', 'Blue', 0, 0), 
('T02', 'Silver', 10, 15000), 
('T03', 'Gold', 25, 40000), 
('T04', 'Platinum', 50, 80000);

-- 2. PENGGUNA (60 Data Otomatis)
INSERT INTO PENGGUNA (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
SELECT 
    'user' || i || '@ui.ac.id', '$2b$12$KIXj9Y8rYfWnq3YHfYlG2OeJw4Y8Bq3xVY3xvA7WjF6qL8sQ9zK2W', 'Mr.', 'Mahasiswa', 'Fasilkom' || i, '+62', '0812345' || TO_CHAR(i, 'FM00'), '2004-01-01', 'Indonesia'
FROM generate_series(1, 60) AS i;

-- 3. PENYEDIA (8 Data)
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;
INSERT INTO PENYEDIA DEFAULT VALUES;

-- 4. MASKAPAI (5 Data)
INSERT INTO MASKAPAI VALUES 
('GA', 'Garuda Indonesia', 1), 
('SQ', 'Singapore Airlines', 2), 
('QZ', 'AirAsia', 3), 
('JT', 'Lion Air', 4), 
('ID', 'Batik Air', 5);

-- 5. MITRA (5 Data)
-- Menggunakan ID Penyedia 4 sampai 8 karena ID di tabel Mitra sifatnya UNIQUE
INSERT INTO MITRA VALUES 
('traveloka@mitra.com', 4, 'Traveloka', '2024-01-01'), 
('tiket@mitra.com', 5, 'Tiket.com', '2024-01-01'), 
('agoda@mitra.com', 6, 'Agoda', '2024-01-01'), 
('pegipegi@mitra.com', 7, 'Pegipegi', '2024-01-01'), 
('booking@mitra.com', 8, 'Booking.com', '2024-01-01');

-- 6. BANDARA (15 Data)
INSERT INTO BANDARA VALUES 
('CGK', 'Soekarno-Hatta', 'Jakarta', 'Indonesia'), ('DPS', 'Ngurah Rai', 'Bali', 'Indonesia'), 
('SUB', 'Juanda', 'Surabaya', 'Indonesia'), ('KNO', 'Kualanamu', 'Medan', 'Indonesia'), 
('YIA', 'Yogyakarta Intl', 'Yogyakarta', 'Indonesia'), ('UPG', 'Sultan Hasanuddin', 'Makassar', 'Indonesia'), 
('BPN', 'Sepinggan', 'Balikpapan', 'Indonesia'), ('BDO', 'Husein Sastranegara', 'Bandung', 'Indonesia'), 
('SRG', 'Ahmad Yani', 'Semarang', 'Indonesia'), ('PLM', 'Sultan Mahmud Badaruddin II', 'Palembang', 'Indonesia'), 
('PDG', 'Minangkabau', 'Padang', 'Indonesia'), ('PKU', 'Sultan Syarif Kasim II', 'Pekanbaru', 'Indonesia'), 
('PNK', 'Supadio', 'Pontianak', 'Indonesia'), ('BTH', 'Hang Nadim', 'Batam', 'Indonesia'), 
('LOP', 'Zainuddin Abdul Madjid', 'Lombok', 'Indonesia');

-- 7. AWARD_MILES_PACKAGE (5 Data)
INSERT INTO AWARD_MILES_PACKAGE VALUES 
('AMP-001', 100000.00, 500), ('AMP-002', 200000.00, 1000), 
('AMP-003', 500000.00, 3000), ('AMP-004', 1000000.00, 7000), 
('AMP-005', 2000000.00, 15000);

-- 8. MEMBER (50 Data Otomatis, pakai user 1 s/d 50)
INSERT INTO MEMBER (email, nomor_member, tanggal_bergabung, id_tier, award_miles, total_miles)
SELECT 
    'user' || i || '@ui.ac.id', 'M' || TO_CHAR(i, 'FM0000'), '2024-01-01', 'T01', 1000, 1000
FROM generate_series(1, 50) AS i;

-- 9. STAF (10 Data Otomatis, pakai user 51 s/d 60)
INSERT INTO STAF (email, id_staf, kode_maskapai)
SELECT 
    'user' || i || '@ui.ac.id', 'S' || TO_CHAR(i - 50, 'FM0000'), 'GA'
FROM generate_series(51, 60) AS i;

-- 10. IDENTITAS (30 Data Otomatis, pakai member 1 s/d 30)
INSERT INTO IDENTITAS (nomor, email_member, tanggal_habis, tanggal_terbit, negara_penerbit, jenis)
SELECT 
    'KTP-317' || TO_CHAR(i, 'FM0000'), 'user' || i || '@ui.ac.id', '2030-01-01', '2020-01-01', 'Indonesia', 'KTP'
FROM generate_series(1, 30) AS i;

-- 11. MEMBER_AWARD_MILES_PACKAGE (20 Data Otomatis)
INSERT INTO MEMBER_AWARD_MILES_PACKAGE (id_award_miles_package, email_member, timestamp)
SELECT 
    'AMP-001', 'user' || i || '@ui.ac.id', CURRENT_TIMESTAMP + (i * interval '1 minute')
FROM generate_series(1, 20) AS i;

-- 12. CLAIM_MISSING_MILES (20 Data Otomatis)
INSERT INTO CLAIM_MISSING_MILES (email_member, maskapai, bandara_asal, bandara_tujuan, tanggal_penerbangan, flight_number, nomor_tiket, kelas_kabin, pnr, timestamp)
SELECT 
    'user' || i || '@ui.ac.id', 'GA', 'CGK', 'DPS', '2024-04-15', 'GA400', 'TKT' || TO_CHAR(i, 'FM0000'), 'Economy', 'PNR' || TO_CHAR(i, 'FM000'), CURRENT_TIMESTAMP + (i * interval '1 minute')
FROM generate_series(1, 20) AS i;

-- 13. TRANSFER (15 Data Otomatis, user 1 transfer ke user 2, dst)
INSERT INTO TRANSFER (email_member_1, email_member_2, timestamp, jumlah, catatan)
SELECT 
    'user' || i || '@ui.ac.id', 'user' || (i+1) || '@ui.ac.id', CURRENT_TIMESTAMP + (i * interval '1 minute'), 500, 'Bagi-bagi miles'
FROM generate_series(1, 15) AS i;

-- 14. HADIAH (10 Data Otomatis)
INSERT INTO HADIAH (kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia)
SELECT 
    'RWD-' || TO_CHAR(i, 'FM000'), 'Voucher Diskon ' || i, i * 1000, 'Deskripsi', '2024-01-01', '2024-12-31', (i % 8) + 1
FROM generate_series(1, 10) AS i;

-- 15. REDEEM (20 Data Otomatis)
INSERT INTO REDEEM (email_member, kode_hadiah, timestamp)
SELECT 
    'user' || i || '@ui.ac.id', 'RWD-001', CURRENT_TIMESTAMP + (i * interval '1 minute')
FROM generate_series(1, 20) AS i;
