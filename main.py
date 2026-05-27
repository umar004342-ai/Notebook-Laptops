"""
Notebook Laptops - Asosiy Flask ilovasi
Har kuni yangi notebook modellarini qo'shish mumkin
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'notebook-laptops-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notebooks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

TELEGRAM_BOT_TOKEN = "8678642754:AAEon7hxfGoBmAbbIeC6UizQx_KmrOSBCuQ"
TELEGRAM_CHAT_ID = "8341090517"

db = SQLAlchemy(app)

# ===================== DATABASE MODELLARI =====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ism = db.Column(db.String(100), nullable=False)
    familya = db.Column(db.String(100), nullable=False)
    telefon = db.Column(db.String(20), nullable=False, unique=True)
    parol_hash = db.Column(db.String(200), nullable=False)
    yaratilgan = db.Column(db.DateTime, default=datetime.utcnow)

    def set_parol(self, parol):
        self.parol_hash = generate_password_hash(parol)

    def tekshir_parol(self, parol):
        return check_password_hash(self.parol_hash, parol)


class Notebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nomi = db.Column(db.String(200), nullable=False)
    brend = db.Column(db.String(100), nullable=False)
    narxi = db.Column(db.Float, nullable=False)
    protsessor = db.Column(db.String(150))
    ram = db.Column(db.String(50))
    disk = db.Column(db.String(100))
    ekran = db.Column(db.String(100))
    grafika = db.Column(db.String(150))
    tavsif = db.Column(db.Text)
    rasm = db.Column(db.String(300))
    kategoriya = db.Column(db.String(50), default='notebook')  # notebook, wifi, aksessuarlar
    mavjud = db.Column(db.Boolean, default=True)
    qoshilgan = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nomi': self.nomi,
            'brend': self.brend,
            'narxi': self.narxi,
            'protsessor': self.protsessor,
            'ram': self.ram,
            'disk': self.disk,
            'ekran': self.ekran,
            'grafika': self.grafika,
            'tavsif': self.tavsif,
            'rasm': self.rasm,
            'kategoriya': self.kategoriya or 'notebook',
            'mavjud': self.mavjud,
        }


class Zakaz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notebook_id = db.Column(db.Integer, db.ForeignKey('notebook.id'))
    vaqt = db.Column(db.DateTime, default=datetime.utcnow)
    holat = db.Column(db.String(50), default='yangi')


# ===================== YORDAMCHI FUNKSIYALAR =====================

def ruxsat_etilgan_fayl(fayl_nomi):
    return '.' in fayl_nomi and fayl_nomi.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def telegram_xabar_yuborish(matn):
    """Faqat matn yuborish"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": matn, "parse_mode": "HTML"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram xato: {e}")
        return False


def telegram_rasm_yuborish(rasm_yoli, caption):
    """Rasm bilan xabar yuborish. Rasm yo'q bo'lsa faqat matn."""
    try:
        if rasm_yoli and os.path.exists(rasm_yoli):
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(rasm_yoli, 'rb') as f:
                r = requests.post(url,
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                    files={"photo": f}, timeout=20)
            if r.status_code == 200:
                return True
        # Rasm yo'q yoki xato - faqat matn
        return telegram_xabar_yuborish(caption)
    except Exception as e:
        print(f"Telegram rasm xato: {e}")
        return telegram_xabar_yuborish(caption)


# ===================== SAHIFALAR =====================

@app.route('/')
def bosh_sahifa():
    notebooklar = Notebook.query.filter_by(mavjud=True).order_by(Notebook.qoshilgan.desc()).limit(12).all()
    return render_template('index.html', notebooklar=notebooklar)


@app.route('/royxatdan-otish', methods=['GET', 'POST'])
def royxatdan_otish():
    if request.method == 'POST':
        data = request.get_json()
        mavjud = User.query.filter_by(telefon=data['telefon']).first()
        if mavjud:
            return jsonify({'muvaffaqiyat': False, 'xato': 'Bu telefon raqam allaqachon ro\'yxatdan o\'tgan'})
        yangi_user = User(ism=data['ism'], familya=data['familya'], telefon=data['telefon'])
        yangi_user.set_parol(data['parol'])
        db.session.add(yangi_user)
        db.session.commit()
        session['user_id'] = yangi_user.id
        session['user_ism'] = yangi_user.ism
        session['user_familya'] = yangi_user.familya
        session['user_telefon'] = yangi_user.telefon
        return jsonify({'muvaffaqiyat': True})
    return render_template('index.html')


@app.route('/kirish', methods=['POST'])
def kirish():
    data = request.get_json()
    user = User.query.filter_by(telefon=data['telefon']).first()
    if user and user.tekshir_parol(data['parol']):
        session['user_id'] = user.id
        session['user_ism'] = user.ism
        session['user_familya'] = user.familya
        session['user_telefon'] = user.telefon
        return jsonify({'muvaffaqiyat': True})
    return jsonify({'muvaffaqiyat': False, 'xato': 'Telefon yoki parol noto\'g\'ri'})


@app.route('/chiqish')
def chiqish():
    session.clear()
    return redirect(url_for('bosh_sahifa'))


# ===================== NOTEBOOK API =====================

@app.route('/api/notebooklar')
def notebooklar_api():
    brend = request.args.get('brend', '')
    qidiruv = request.args.get('q', '')
    kategoriya = request.args.get('kategoriya', '')

    query = Notebook.query.filter_by(mavjud=True)

    if brend:
        query = query.filter(Notebook.brend.ilike(f'%{brend}%'))

    if kategoriya:
        query = query.filter(Notebook.kategoriya == kategoriya)

    if qidiruv:
        query = query.filter(db.or_(
            Notebook.nomi.ilike(f'%{qidiruv}%'),
            Notebook.brend.ilike(f'%{qidiruv}%'),
            Notebook.protsessor.ilike(f'%{qidiruv}%')
        ))

    notebooklar = query.order_by(Notebook.qoshilgan.desc()).all()
    return jsonify([n.to_dict() for n in notebooklar])


@app.route('/api/notebook/<int:id>')
def notebook_detail(id):
    notebook = Notebook.query.get_or_404(id)
    return jsonify(notebook.to_dict())


@app.route('/zakaz', methods=['POST'])
def zakaz_berish():
    """Zakaz berish - Telegramga RASM bilan yuborish"""
    if 'user_id' not in session:
        return jsonify({'muvaffaqiyat': False, 'xato': 'Iltimos avval tizimga kiring'})

    data = request.get_json()
    notebook_id = data.get('notebook_id')
    miqdor = max(1, int(data.get('miqdor', 1)))

    notebook = Notebook.query.get(notebook_id)
    if not notebook:
        return jsonify({'muvaffaqiyat': False, 'xato': 'Mahsulot topilmadi'})

    # Zakazni saqlash
    zakaz = Zakaz(user_id=session['user_id'], notebook_id=notebook_id)
    db.session.add(zakaz)
    db.session.commit()

    # Kategoriya emoji va nomi
    kat = notebook.kategoriya or 'notebook'
    kat_emoji = {'notebook': '💻', 'wifi': '📶', 'aksessuarlar': '🎧'}.get(kat, '📦')
    kat_nomi = {'notebook': 'Notebook/Laptop', 'wifi': 'Wi-Fi Router', 'aksessuarlar': 'Aksessuarlar'}.get(kat, 'Mahsulot')

    # Narxni so'mda chiroyli formatlash
    def som(n):
        return f"{int(n):,}".replace(",", " ") + " so'm"

    # Telegram xabari matni
    vaqt = datetime.now().strftime('%Y-%m-%d %H:%M')
    xabar = f"""🛒 <b>YANGI ZAKAZ!</b>

👤 <b>Mijoz:</b> {session['user_ism']} {session['user_familya']}
📞 <b>Telefon:</b> {session['user_telefon']}

{kat_emoji} <b>{kat_nomi}:</b> {notebook.nomi}
🏷 <b>Brend:</b> {notebook.brend}
🔢 <b>Miqdor:</b> {miqdor} dona
💰 <b>Narxi:</b> {som(notebook.narxi)} × {miqdor} = <b>{som(notebook.narxi * miqdor)}</b>

🕐 <b>Vaqt:</b> {vaqt}
📍 Toshkent, Malika bozori B20 va B13 dokon"""

    # Rasm bilan yuborish
    rasm_yoli = None
    if notebook.rasm and notebook.rasm not in ['', 'default.jpg']:
        rasm_yoli = os.path.join(app.config['UPLOAD_FOLDER'], notebook.rasm)

    telegram_rasm_yuborish(rasm_yoli, xabar)

    return jsonify({'muvaffaqiyat': True, 'xabar': 'Zakazingiz qabul qilindi! Tez orada siz bilan bog\'lanamiz.'})


# ===================== ADMIN PANEL =====================

@app.route('/admin')
def admin_panel():
    if not session.get('user_id'):
        return redirect(url_for('bosh_sahifa'))
    notebooklar = Notebook.query.order_by(Notebook.qoshilgan.desc()).all()
    return render_template('admin.html', notebooklar=notebooklar)


@app.route('/admin/notebook-qosh', methods=['POST'])
def notebook_qosh():
    if not session.get('user_id'):
        return jsonify({'muvaffaqiyat': False, 'xato': 'Tizimga kiring'})
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        rasm_nomi = ''
        if 'rasm' in request.files:
            fayl = request.files['rasm']
            if fayl and fayl.filename and ruxsat_etilgan_fayl(fayl.filename):
                rasm_nomi = secure_filename(f"{int(datetime.now().timestamp())}_{fayl.filename}")
                fayl.save(os.path.join(upload_folder, rasm_nomi))

        nomi = request.form.get('nomi', '').strip()
        brend = request.form.get('brend', '').strip()
        narxi_str = request.form.get('narxi', '0').strip()
        kategoriya = request.form.get('kategoriya', 'notebook').strip()

        if not nomi:
            return jsonify({'muvaffaqiyat': False, 'xato': 'Model nomi kiritilmagan!'})
        if not brend:
            return jsonify({'muvaffaqiyat': False, 'xato': 'Brend tanlanmagan!'})

        try:
            narxi = float(narxi_str)
        except:
            narxi = 0.0

        notebook = Notebook(
            nomi=nomi, brend=brend, narxi=narxi,
            protsessor=request.form.get('protsessor', ''),
            ram=request.form.get('ram', ''),
            disk=request.form.get('disk', ''),
            ekran=request.form.get('ekran', ''),
            grafika=request.form.get('grafika', ''),
            tavsif=request.form.get('tavsif', ''),
            rasm=rasm_nomi,
            kategoriya=kategoriya,
        )
        db.session.add(notebook)
        db.session.commit()
        return jsonify({'muvaffaqiyat': True, 'id': notebook.id})

    except Exception as e:
        db.session.rollback()
        print(f"Xato: {e}")
        return jsonify({'muvaffaqiyat': False, 'xato': f'Xatolik: {str(e)}'})


@app.route('/admin/notebook-ochir/<int:id>', methods=['DELETE'])
def notebook_ochir(id):
    if not session.get('user_id'):
        return jsonify({'muvaffaqiyat': False})
    notebook = Notebook.query.get_or_404(id)
    notebook.mavjud = False
    db.session.commit()
    return jsonify({'muvaffaqiyat': True})


# ===================== DEMO MALUMOTLAR =====================

def demo_malumot_qosh():
    if Notebook.query.count() > 0:
        return
    demo = [
        {'nomi': 'HP Pavilion 15-eg2000', 'brend': 'HP', 'narxi': 650, 'protsessor': 'Intel Core i5-1235U', 'ram': '8GB DDR4', 'disk': '512GB NVMe SSD', 'ekran': '15.6" FHD IPS', 'grafika': 'Intel Iris Xe', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'ASUS VivoBook 15 X1502', 'brend': 'ASUS', 'narxi': 580, 'protsessor': 'Intel Core i3-1215U', 'ram': '8GB DDR4', 'disk': '256GB SSD', 'ekran': '15.6" FHD', 'grafika': 'Intel UHD', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'Lenovo IdeaPad 3 Gen 7', 'brend': 'Lenovo', 'narxi': 520, 'protsessor': 'AMD Ryzen 5 5500U', 'ram': '8GB DDR4', 'disk': '512GB SSD', 'ekran': '15.6" FHD', 'grafika': 'AMD Radeon', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'Dell Inspiron 15 3520', 'brend': 'Dell', 'narxi': 620, 'protsessor': 'Intel Core i5-1235U', 'ram': '16GB DDR4', 'disk': '512GB SSD', 'ekran': '15.6" FHD', 'grafika': 'Intel Iris Xe', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'Acer Aspire 5 A515', 'brend': 'Acer', 'narxi': 490, 'protsessor': 'AMD Ryzen 5 5625U', 'ram': '8GB DDR4', 'disk': '512GB SSD', 'ekran': '15.6" FHD IPS', 'grafika': 'AMD Radeon', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'MSI Modern 15', 'brend': 'MSI', 'narxi': 750, 'protsessor': 'Intel Core i7-1255U', 'ram': '16GB DDR4', 'disk': '512GB NVMe', 'ekran': '15.6" FHD 144Hz', 'grafika': 'NVIDIA MX450', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'HP Gaming Victus 15', 'brend': 'HP', 'narxi': 980, 'protsessor': 'Intel Core i5-12450H', 'ram': '16GB DDR5', 'disk': '512GB SSD', 'ekran': '15.6" FHD 144Hz', 'grafika': 'NVIDIA RTX 3050', 'rasm': '', 'kategoriya': 'notebook'},
        {'nomi': 'ASUS ROG Strix G15', 'brend': 'ASUS', 'narxi': 1350, 'protsessor': 'AMD Ryzen 7 6800H', 'ram': '16GB DDR5', 'disk': '1TB NVMe SSD', 'ekran': '15.6" FHD 144Hz', 'grafika': 'NVIDIA RTX 3060', 'rasm': '', 'kategoriya': 'notebook'},
    ]
    for d in demo:
        db.session.add(Notebook(**d, tavsif='Premium sifatli mahsulot'))
    db.session.commit()
    print("Demo ma'lumotlar qo'shildi!")


# ===================== ISHGA TUSHIRISH =====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Eski DB ga kategoriya ustunini avtomatik qo'shish
        try:
            import sqlalchemy
            inspector = sqlalchemy.inspect(db.engine)
            cols = [c['name'] for c in inspector.get_columns('notebook')]
            if 'kategoriya' not in cols:
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text("ALTER TABLE notebook ADD COLUMN kategoriya VARCHAR(50) DEFAULT 'notebook'"))
                    conn.commit()
                print("kategoriya ustuni qo'shildi!")
        except Exception as e:
            print(f"Migration: {e}")
        demo_malumot_qosh()
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(debug=False, port=5000)
