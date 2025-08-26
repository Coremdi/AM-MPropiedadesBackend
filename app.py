from flask import Flask, session
from flask_cors import CORS
from admin_login import admin_bp
from properties import properties_bp
from update_properties import admin_property_bp
from create_properties import create_property_bp
from delete_property import delete_property_bp
from upload_images import upload_images_bp
from delete_images import bulk_delete_images_bp
from reset_password import resetpassword_bp
from flask_mail import Mail, Message
from setup_admin import create_user_bp


app = Flask(__name__)
app.secret_key = 'Rebecca170694!'  # Change this for production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # True in production with HTTPS
app.config['JSON_AS_ASCII'] = False
CORS(app, supports_credentials=True)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'coremdi3@gmail.com'
app.config['MAIL_PASSWORD'] = 'lsua dizx uhsw bxnz'  # <-- Replace with Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = ('AM&M Propiedades', 'coremdi3@gmail.com')

mail = Mail(app)


# Register blueprints
app.register_blueprint(admin_bp, url_prefix='/api')
app.register_blueprint(properties_bp, url_prefix='/api')
app.register_blueprint(admin_property_bp, url_prefix='/api')
app.register_blueprint(create_property_bp, url_prefix='/api')
app.register_blueprint(delete_property_bp, url_prefix='/api')
app.register_blueprint(upload_images_bp, url_prefix='/api')
app.register_blueprint(bulk_delete_images_bp, url_prefix='/api')
app.register_blueprint(resetpassword_bp, url_prefix='/api')
app.register_blueprint(create_user_bp, url_prefix='/api')





if __name__ == '__main__':
    app.run(debug=True)