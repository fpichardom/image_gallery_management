from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werzeug.utils import secure_filename
import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import List, Optional
import os
import uuid
from datetime import datetime, timezone

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///couples_gallery.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Image(db.Model):
    id: so.Mapped[str] = so.mapped_column(primary_key=True, default=uuid.uuid4)
    filename: so.Mapped[str] = so.mapped_column(sa.String(100),nullable=False)
    path: so.Mapped[str] = so.mapped_column(sa.String(200),nullable=False)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    messages:so.WriteOnlyMapped['Message'] = so.relationship(back_populates='image')

class Message(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)
    author: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    image_id: so.Mapped[str] = so.mapped_column(sa.ForeignKey('image.id'), nullable=False)
    image: so.Mapped[Image] = so.relationship(back_populates='messages')


@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/gallery')
def gallery():
    stmt = sa.select(Image).order_by(Image.timestamp.desc())
    images = db.session.scalars(stmt).all()
    return render_template('gallery.html', images=images)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        #if 'file' not in request.files:
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            image_id = str(uuid.uuid4())
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_id)
            os.makedirs(image_path, exist_ok=True)
            file_path = os.path.join(image_path, filename)
            file.save(file_path)

            new_image = Image(id=image_id, filename=filename, path=file_path)
            db.session.add(new_image)
            db.session.commit()

            flash('Image uploaded successfully', 'success')
            return redirect(url_for('gallery'))
    return render_template('upload.html')

@app.route('/batch_upload', methods=['GET', 'POST'])
def batch_upload():
    if request.method == 'POST':
        files = request.files.getlist('files')
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                image_id = str(uuid.uuid4())
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_id)
                os.makedirs(image_path, exist_ok=True)
                file_path = os.path.join(image_path, filename)
                file.save(file_path)

                new_image = Image(id=image_id, filename=filename, path=file_path)
                db.session.add(new_image)
        db.session.commit()
        flash('All images uploaded successfully', 'success')
        return redirect(url_for('thumbnail_view'))
    return render_template('batch_upload.html')

@app.route('/thumbnail_view')
def thumbnail_view():
    stmt = sa.select(Image).order_by(Image.timestamp.desc())
    images = db.session.scalars(stmt).all()
    return render_template('thumbnail_view.html', images=images)

@app.route('add_message/<image_id>', methods=['GET', 'POST'])
def add_message(image_id):
    stmt = sa.select(Image).where(Image.id == image_id)
    image = db.session.scalars(stmt)
    if image is None:
        flash('Image not found', 'error')
        return redirect(url_for('thumbnail_view'))
    
    if request.method == 'POST':
        content = request.form['content']
        author = request.form['author']
        new_message = Message(content=content, author=author, image_id=image_id)
        db.session.add(new_message)
        db.session.commit()
        flash('Message added successfully', 'success')
        return redirect(url_for('thumbnail_view'))

    if request.method == 'POST':
        content = request.form['content']
        author = request.form['author']
        new_message = Message(content=content, author=author, image_id=image_id)
        db.session.add(new_message)
        db.session.commit()
        flash('Message added successfully', 'success')
        return redirect(url_for('thumbnail_view'))
    return render_template('add_message.html', image=image)

if __name__ == '__main__':
    app.run(debug=True)