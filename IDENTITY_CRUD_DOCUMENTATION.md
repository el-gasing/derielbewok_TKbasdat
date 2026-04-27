# Sistem CRUD Identitas Member - AeroMiles

## 📋 Deskripsi

Sistem CRUD (Create, Read, Update, Delete) untuk memungkinkan **Member** mengelola dokumen identitas mereka sendiri. Fitur ini hanya dapat diakses oleh pengguna dengan role **Member**.

## ✨ Fitur

### 1. **Tambah Identitas (Create)**
- Member dapat menambahkan dokumen identitas baru
- Jenis dokumen yang didukung:
  - Paspor
  - KTP (Kartu Tanda Penduduk)
  - SIM (Surat Izin Mengemudi)
- Validasi:
  - Nomor dokumen harus unik untuk setiap member
  - Tanggal terbit harus lebih awal dari tanggal habis
- Field yang diisi:
  - Nomor Dokumen (wajib)
  - Jenis Dokumen (dropdown, wajib)
  - Negara Penerbit (wajib)
  - Tanggal Terbit (wajib)
  - Tanggal Habis (wajib)

### 2. **Daftar Identitas (Read)**
- Member dapat melihat semua dokumen identitas yang telah didaftarkan
- Tabel menampilkan:
  - Nomor Dokumen
  - Jenis Dokumen
  - Negara Penerbit
  - Tanggal Terbit
  - Tanggal Habis
  - Status (Aktif/Kadaluarsa/Tidak Aktif)
  - Aksi (Edit/Hapus)
- Status kedaluwarsa dihitung otomatis berdasarkan tanggal hari ini

### 3. **Edit Identitas (Update)**
- Member dapat memperbarui data identitas
- **Nomor dokumen tidak dapat diubah** (read-only)
- Field yang dapat diubah:
  - Jenis Dokumen
  - Negara Penerbit
  - Tanggal Terbit
  - Tanggal Habis
- Validasi sama seperti saat menambah

### 4. **Hapus Identitas (Delete)**
- Member dapat menghapus dokumen identitas yang tidak lagi relevan
- Konfirmasi ditampilkan sebelum penghapusan
- Menggunakan modal konfirmasi yang user-friendly

## 🗂️ Struktur File

### Backend
```
auth_system/
├── models.py              # Model MemberIdentity
├── forms.py               # AddMemberIdentityForm, EditMemberIdentityForm
├── views.py               # CRUD views (add, list, edit, delete)
└── urls.py                # URL routing
```

### Frontend
```
templates/auth_system/
├── member_identities_list.html    # Halaman daftar identitas
├── add_member_identity.html       # Form tambah identitas
└── edit_member_identity.html      # Form edit identitas
```

## 🔐 Keamanan

### Access Control
- Semua endpoint dilindungi dengan decorator `@member_required`
- Hanya user dengan role Member yang dapat mengakses
- Validasi ownership: member hanya bisa mengelola identitas miliknya sendiri

### Validasi Data
- Unique constraint pada kombinasi member + document_number
- Validasi tanggal: issued_date < expiry_date
- CSRF protection pada semua form

## ️ Model Database

### MemberIdentity
```python
class MemberIdentity(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('passport', 'Pasport'),
        ('ktp', 'KTP'),
        ('sim', 'SIM'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('expired', 'Kadaluarsa'),
        ('inactive', 'Tidak Aktif'),
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='identities')
    document_number = models.CharField(max_length=50)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    country_issued = models.CharField(max_length=100)
    issued_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['member', 'document_number']
```

## 🌐 URL Endpoints

| Endpoint | Method | View | Deskripsi |
|----------|--------|------|-----------|
| `/identitas/` | GET | `member_identities_list` | Daftar identitas member |
| `/identitas/tambah/` | GET, POST | `add_member_identity` | Tambah identitas baru |
| `/identitas/edit/<id>/` | GET, POST | `edit_member_identity` | Edit identitas |
| `/identitas/hapus/<id>/` | POST | `delete_member_identity` | Hapus identitas |

## 🎨 UI/UX Features

### Design System
- Modern, clean interface dengan color scheme AeroMiles
- Responsive design (mobile-friendly)
- Consistent styling dengan halaman lain

### User Experience
- **Alert Messages**: Notifikasi sukses/error dengan color coding
- **Modal Confirmation**: Konfirmasi hapus dengan modal yang elegan
- **Empty State**: Pesan kosong dengan call-to-action yang jelas
- **Form Validation**: Real-time validation dengan pesan error yang jelas
- **Read-only Fields**: Nomor dokumen dibuat read-only saat edit dengan visual cue

### Interactive Elements
- Hover effects pada tombol
- Smooth transitions
- Animated modal slide-in
- Click-outside-to-close modal

## 📝 Cara Penggunaan

### Sebagai Member

1. **Login** ke akun member Anda
2. Navigasi ke menu **"Identitas Saya"**
3. **Tambah Identitas**:
   - Klik tombol "Tambah Identitas"
   - Isi semua field yang diperlukan
   - Klik "Simpan"
4. **Edit Identitas**:
   - Klik tombol "Edit" pada identitas yang ingin diubah
   - Update field yang diinginkan (nomor dokumen tidak dapat diubah)
   - Klik "Simpan Perubahan"
5. **Hapus Identitas**:
   - Klik tombol "Hapus" pada identitas yang ingin dihapus
   - Konfirmasi pada modal yang muncul
   - Klik "Hapus" untuk menghapus permanen

## 🔧 Testing

### Manual Testing Checklist

#### Create (Tambah)
- [ ] Form tampil dengan semua field yang diperlukan
- [ ] Validasi nomor dokumen unik
- [ ] Validasi tanggal terbit < tanggal habis
- [ ] Sukses menambah identitas baru
- [ ] Redirect ke halaman daftar setelah sukses

#### Read (Daftar)
- [ ] Semua identitas member ditampilkan
- [ ] Status badge tampil dengan warna yang benar (Aktif=hijau, Kadaluarsa=merah)
- [ ] Empty state tampil jika belum ada identitas
- [ ] Data ter-sorting dengan benar

#### Update (Edit)
- [ ] Form edit menampilkan data yang benar
- [ ] Nomor dokumen read-only
- [ ] Validasi tanggal tetap berfungsi
- [ ] Sukses update data
- [ ] Redirect ke halaman daftar setelah sukses

#### Delete (Hapus)
- [ ] Modal konfirmasi tampil
- [ ] Nomor dokumen ditampilkan di modal
- [ ] Tombol Batal menutup modal
- [ ] Tombol Hapus menghapus data
- [ ] Redirect ke halaman daftar setelah sukses

## 🚀 Deployment

Sistem sudah siap digunakan! Pastikan:
1. Database sudah di-migrate
2. User sudah login sebagai member
3. Virtual environment sudah aktif

## 📊 Status Kedaluwarsa

Status identitas dihitung otomatis:
- **Aktif**: Tanggal habis > tanggal hari ini
- **Kadaluarsa**: Tanggal habis < tanggal hari ini
- **Tidak Aktif**: Status manual (jika diperlukan)

Perhitungan dilakukan setiap kali halaman daftar identitas dibuka.

## 🎯 Best Practices Implemented

1. ✅ **Security**: Authentication & authorization dengan decorator
2. ✅ **Validation**: Server-side validation pada forms
3. ✅ **UX**: Clear feedback dengan messages framework
4. ✅ **UI**: Consistent design dengan component lain
5. ✅ **Data Integrity**: Unique constraints dan foreign keys
6. ✅ **CSRF Protection**: Token pada semua form
7. ✅ **Responsive Design**: Mobile-friendly layout
8. ✅ **Accessibility**: Semantic HTML dan proper labels

## 📞 Support

Jika ada masalah atau pertanyaan, silakan hubungi tim development.
