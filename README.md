## 📂 Project Structure

```text
personalized_gifts/ 
├── app.py                      # Main Flask Application & Routes 
├── models.py                   # Database Models (User, Interaction) & Product Loading 
├── recommender.py              # AI Logic (Content-Based, Collaborative, Hybrid Engines) 
├── products.py                 # Web Scrapers (Meevyy, Mark & Graham) 
├── optgiftai_database.csv      # Static Product Dataset (35 items) 
├── requirements.txt            # Python Dependencies 
├── README.md                   # Project Documentation 
├── static/ 
│   ├── css/ 
│   │   └── style.css           # Premium "Amex-style" CSS Styling 
│   └── js/ 
│       └── main.js             # Frontend logic (AJAX, Popups, Compare Logic) 
└── templates/ 
    ├── base.html               # Base layout (Navbar, Footer, Toast Notifications) 
    ├── login.html              # Login/Signup Page 
    ├── wizard.html             # Cold-Start Preferences Wizard 
    ├── dashboard.html          # Main Dashboard (Displays 3 Recommendation Rows) 
    ├── product_card.html       # Reusable Product Component (w/ Confidence Score) 
    ├── cart.html               # Shopping Cart Page 
    ├── profile.html            # User Profile & Interests View 
    └── update_preferences.html # Form to Edit User Interests```
	


Pip Dependencies:
$ pip list
Package               Version
--------------------- -----------
attrs                  25.4.0
bcrypt                 4.0.1
beautifulsoup4         4.14.3
blinker                1.9.0
bs4                    0.0.2
certifi                2025.11.12
cffi                   2.0.0
charset-normalizer     3.4.4
click                  8.3.1
colorama               0.4.6
exceptiongroup         1.3.1
filelock               3.20.1
Flask                  3.0.0
Flask-Login            0.6.3
Flask-SQLAlchemy       3.1.1
fsspec                 2025.12.0
greenlet               3.3.0
h11                    0.16.0
huggingface-hub        0.14.1
idna                   3.11
intel-cmplr-lib-ur     2025.3.1
intel-openmp           2025.3.1
itsdangerous           2.2.0
Jinja2                 3.1.6
joblib                 1.5.3
MarkupSafe             3.0.3
mpmath                 1.3.0
networkx               3.4.2
nltk                   3.9.2
numpy                  1.26.0
outcome                1.3.0.post0
packaging              25.0
pandas                 2.1.1
pillow                 12.0.0
pip                    25.3
pycparser              2.23
PySocks                1.7.1
python-dateutil        2.9.0.post0
python-dotenv          1.2.1
pytz                   2025.2
PyYAML                 6.0.3
regex                  2025.11.3
requests               2.32.5
safetensors            0.7.0
scikit-learn           1.3.1
scipy                  1.15.3
selenium               4.39.0
sentence-transformers  2.2.2
sentencepiece          0.2.1
setuptools             58.1.0
six                    1.17.0
sniffio                1.3.1
sortedcontainers       2.4.0
soupsieve              2.8.1
SQLAlchemy             2.0.45
sympy                  1.14.0
tcmlib                 1.4.1
threadpoolctl          3.6.0
tokenizers             0.13.3
torch                  2.9.1+cpu
torchaudio             2.9.1+cpu
torchvision            0.24.1+cpu
tqdm                   4.67.1
transformers           4.30.2
trio                   0.32.0
trio-websocket         0.12.2
typing_extensions      4.15.0
tzdata                 2025.3
umf                    1.0.2
urllib3                2.6.2
webdriver-manager      4.0.2
websocket-client       1.9.0
Werkzeug               3.1.4
wsproto                1.3.2