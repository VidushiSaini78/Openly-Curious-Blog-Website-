from flask import Flask,session, render_template, redirect, request, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json 
from flask_bcrypt import Bcrypt
import re
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import os
import math

app = Flask(__name__)
local_server = True
with open('config.json', 'r') as c:
    params = json.load(c)["params"]

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params["local_uri"]
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params["prod_uri"]

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  
app.config['upload_location'] = params["upload_location"]
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Databases 
class Users(db.Model):
    __tablename__ = "users"
    S_No= db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(20), unique=True, nullable=False)
    Password = db.Column(db.String(64), nullable=False)  

    def __init__(self, Email, Password):
        self.Email = Email
        self.Password = Password

class Contact(db.Model):
    __tablename__ = "contacts"
    S_No = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(15), unique=False, nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Phone_No = db.Column(db.String(12), nullable=False)  
    Message = db.Column(db.String(50), nullable=False)
    Issued_Raised = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, Name, Email, Phone_No, Message, Issued_Raised):
        self.Name = Name
        self.Email = Email
        self.Phone_No = Phone_No
        self.Message = Message
        self.Issued_Raised = Issued_Raised

class Posts(db.Model):
    __tablename__ = "posts"
    S_No = db.Column(db.Integer, primary_key=True)
    Blog_Title = db.Column(db.String(50), nullable=False)
    Blog_Tagline = db.Column(db.String(50), nullable=False)
    Blog_Content = db.Column(db.String(500), nullable=False)
    Posted_On = db.Column(db.Date, nullable=False)
    Blog_Slug = db.Column(db.String(30), nullable=False)
    Img_Url = db.Column(db.String(50) , nullable=False)
    User_Email = db.Column(db.String(50) , nullable=False) 

    def __init__(self, Blog_Title, Blog_Tagline, Blog_Content, Posted_On, Blog_Slug, Img_Url, User_Email ):
        self.Blog_Title = Blog_Title
        self.Blog_Tagline = Blog_Tagline
        self.Blog_Content = Blog_Content
        self.Posted_On = Posted_On
        self.Blog_Slug = Blog_Slug
        self.Img_Url = Img_Url
        self.User_Email = User_Email

# Starting Page
@app.route("/")
def starting_page():
    return render_template("home_page.html" , params=params)

@app.route("/admin_login", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        email = request.form.get("email").strip()  # Strip whitespace
        password = request.form.get("password").strip()  # Strip whitespace
        
        if not email or not password:
            flash("Please enter both email and password.", "error")
            return redirect(url_for('admin'))
        
        # Debug output
        print(f"Entered email: {email}, Expected email: {params['admin_useremail']}")
        print(f"Entered password: {password}, Expected password: {params['admin_pass']}")
        
        # Ensure the password is compared correctly
        if email == params["admin_useremail"] and password == params["admin_pass"]:  
            session['admin_logged_in'] = True  
            flash("Login successful!", "success")
            return redirect(url_for('admin_dashboard'))  
        else:
            flash("Invalid email or password. Please try again.", "error")
            return redirect(url_for('admin')) 
    
    return render_template("admin_login.html" , params=params) 

@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for('admin')) 
    total_users = Users.query.count()
    today = datetime.utcnow().date()
    total_posts_today = Posts.query.filter(Posts.Posted_On >= today).count()
    all_posts = Posts.query.order_by(Posts.Posted_On.desc()).all()

    return render_template("admin_dashboard.html",params=params, total_users=total_users, total_posts_today=total_posts_today, all_posts=all_posts)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Posts.query.get_or_404(post_id)
    return render_template("post.html", post=post, params = params)

# Login Function 
@app.route("/login", methods=["GET", "POST"]) 
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return redirect(url_for('login'))

        user = Users.query.filter_by(Email=email).first()

        if user:
            print("Password entered:", password)  # Debugging: User's entered password
            print("Password hash in database:", user.Password)  # Debugging: Database-stored hash

            if bcrypt.check_password_hash(user.Password, password):
                session['Email'] = email
                return redirect(url_for('index'))
            else:
                flash("Invalid email or password. Please try again.", "error")
        else:
            flash("Email not found.", "error")

        return redirect(url_for('login'))

    return render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        Email = request.form.get("email")
        Password = request.form.get("password")
        confirmpassword = request.form.get("confirmpassword")

        if not Email or not Password or not confirmpassword:
            flash("All fields are required.", "error")
            return render_template("register.html")
        
        user = Users.query.filter_by(Email=Email).first()
        if user:
            flash("Email already registered. Please log in.", "error")
            return redirect(url_for('login'))

        if confirmpassword != Password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        
        hashed_password = bcrypt.generate_password_hash(Password).decode('utf-8')
        new_user = Users(Email=Email, Password=hashed_password)  # Note `Password` matches ORM
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template("register.html")

# Logout Function 
@app.route("/logout")
def log():
    return render_template("home_page.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        new_password = request.form.get("password")
        
        user = Users.query.filter_by(Email=email).first()
        
        if user:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            print("Generated hash for new password:", hashed_password)  # Debugging: Check new hash
            user.Password = hashed_password  # Ensure `Password` matches the ORM field name
            db.session.commit()
            flash("Password updated successfully!", "success")
            return redirect(url_for("login"))
        else:
            flash("Email not found. Please check and try again.", "danger")
    
    return render_template("forget_pass.html")

# About Page
@app.route("/about")
def about():
    return render_template("about.html", params=params)

# Contact Us
@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        Name = request.form.get('name')
        Email = request.form.get('email')
        Phone_No = request.form.get('phone')
        Message = request.form.get('msg')
        
        if not Name or not Email or not Phone_No or not Message:
            flash("Please fill out all fields.", "error")
            return render_template("contact.html", params=params)
        
        if not Phone_No.isdigit() or len(Phone_No) != 10:
            flash("Phone number must be exactly 10 digits.", "error")
            return render_template("contact.html", params=params)

        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        recent_submission = Contact.query.filter(
            (Contact.Email == Email) | (Contact.Phone_No == Phone_No),
            Contact.Issued_Raised >= twenty_four_hours_ago
        ).first()

        if recent_submission:
            flash("You can only submit one query every 24 hours. Please try again later.", "error")
            return render_template("contact.html", params=params)

        try:
            user_query = Contact(
                Name=Name,
                Email=Email,
                Phone_No=Phone_No,
                Message=Message,
                Issued_Raised=datetime.now()
            )
            db.session.add(user_query)
            db.session.commit()
            flash("Your message has been submitted successfully!", "success")
            return redirect(url_for('contact')) 
        except Exception as e:
            db.session.rollback() 
            flash("An error occurred while submitting your message. Please try again later.", "error")
            print(f"Error: {e}")

    return render_template("contact.html", params=params)


# @app.route("/index")
# def index():

#     total_post = Posts.query.filter_by().all()[0:params["no_of_post"]]
#     return render_template("index.html", params=params , post=total_post)

@app.route("/index")
def index():
    # Fetch all posts from the database
    posts = Posts.query.all()  # Check if this fetches your posts correctly
    last = math.ceil(len(posts) / int(params['no_of_post']))
    
    # Get the page number from the query string, default to 1 if not provided
    page = request.args.get('page')
    if not str(page).isnumeric() or int(page) < 1:
        page = 1
    else:
        page = int(page)

    # Pagination logic
    posts = posts[(page - 1) * int(params['no_of_post']): page * int(params['no_of_post'])]
    
    # Handle previous and next page URLs
    if page == 1:
        prev = "#"
        next = "/index?page=" + str(page + 1) if len(posts) == int(params['no_of_post']) else "#"
    elif page == last:
        prev = "/index?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/index?page=" + str(page - 1)
        next = "/index?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)





@app.route("/post/<string:slug>" , methods=['GET'])
def post(slug):
    post_search = Posts.query.filter_by(Blog_Slug=slug).first()
    return render_template("post.html" , params= params, post=post_search)



@app.route("/user_dashboard")
def user_page():
    user_email = session.get('Email')
    user_posts = Posts.query.filter_by(User_Email=user_email).all()
    return render_template('user_dashboard.html',params=params, posts=user_posts , user_email=user_email)

@app.route("/add_post", methods=['GET', 'POST'])
def add_post():
    if request.method == 'POST':
        Blog_Title = request.form.get("Blog_Title")
        Blog_Tagline = request.form.get("Blog_Tagline")
        Blog_Content = request.form.get("Blog_Content")
        Blog_Slug = request.form.get("Blog_Slug")
        Img_Url = request.files['Img_Url']

        # Check mandatory fields
        if not all([Blog_Title, Blog_Tagline, Blog_Content, Img_Url]):
            flash("All mandatory fields must be filled out.", "error")
            return render_template("add_post.html", params=params)

        word_count = len(Blog_Content.split())
        if word_count < 100:
            flash("Blog content must contain at least 100 words.", "error")
            return render_template("add_post.html", params=params)

        # Generate slug if not provided
        if not Blog_Slug.strip():
            Blog_Slug = generate_slug(Blog_Title)
        Blog_Slug = make_slug_unique(Blog_Slug)

        if Img_Url:
            img_filename = secure_filename(Img_Url.filename)  # Ensure filename is safe
            Img_Url.save(os.path.join(app.config['upload_location'], img_filename))  # Define UPLOAD_FOLDER in your config
            Img_Url = img_filename  # Save only the filename in the database

        Email = session.get('Email')
        New_Post = Posts(
            Blog_Title=Blog_Title,
            Blog_Tagline=Blog_Tagline,
            Blog_Content=Blog_Content,
            Posted_On=datetime.utcnow(),
            Blog_Slug=Blog_Slug,
            Img_Url=Img_Url,
            User_Email=Email
        )

        db.session.add(New_Post)
        db.session.commit()

        flash("Post added successfully!", "success")
        return redirect(url_for('user_page'))  

    return render_template("add_post.html", params=params)

def generate_slug(title):
    if title.strip(): 
        slug = re.sub(r'[\s]+', '-', title.strip().lower())
        slug = re.sub(r'[^a-z0-9-]', '', slug)
    else:
        slug = ""
    return slug

def make_slug_unique(slug):
    original_slug = slug
    counter = 1
    existing_slugs = set(post.Blog_Slug for post in Posts.query.all())
    while slug in existing_slugs:
        slug = f"{original_slug}-{counter}"
        counter += 1
    existing_slugs.add(slug)
    return slug


@app.route('/edit/<int:S_No>', methods=['GET', 'POST'])
def edit_post(S_No):
    post = Posts.query.get_or_404(S_No)
    if request.method == 'POST':
        # Check if any required field is empty
        if not request.form['Blog_Title'] or not request.form['Blog_Tagline'] or not request.form['Blog_Content'] or not request.form['Img_Url']:
            flash("All fields are required!", "error")
            return redirect(url_for('edit_post', S_No=post.S_No))
        
        # Update post fields
        post.Blog_Title = request.form['Blog_Title']
        post.Blog_Tagline = request.form['Blog_Tagline']
        post.Blog_Content = request.form['Blog_Content']
        post.Img_Url = request.form['Img_Url']
        
        # Generate and update slug
        Slug = generate_slug(post.Blog_Title)
        Slug = make_slug_unique(Slug)
        post.Blog_Slug = Slug
        post.Posted_On = datetime.utcnow()

        try:
            db.session.commit()
            flash("Post updated successfully!", "success")
            return redirect(url_for('user_page'))
        except:
            db.session.rollback()
            flash("Error occurred while updating the post.", "error")
            return redirect(url_for('edit_post', S_No=post.S_No))

    return render_template("edit.html", params=params, post=post)
    
# Route for deleting a post
@app.route('/delete_post/<int:s_no>', methods=['POST'])
def delete_post(s_no):
    post_to_delete = Posts.query.get(s_no)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('user_page'))

@app.route('/delete_admin/<int:s_no>', methods=['POST'])
def delete_admin(s_no):
    post = Posts.query.get(s_no)
    
    if post:
        if post.image_path and os.path.exists(post.image_path):
            try:
                os.remove(post.image_path)  # Delete the image file
            except Exception as e:
                flash("Error deleting the image: {}".format(str(e)), "error")
        
        db.session.delete(post) 
        db.session.commit()       
        flash("Post deleted successfully!", "success")
    else:
        flash("Post not found.", "error")
    return redirect(url_for('admin_dashboard'))




if __name__ == "__main__":
    app.run(debug=True)
