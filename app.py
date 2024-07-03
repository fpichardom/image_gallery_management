from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import List, Optional
import os
import uuid
from datetime import datetime, timezone
import sys
from flask import jsonify


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

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'path': self.path,
            'timestamp': self.timestamp
        }

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
    #image_data = [{"id": img.id, "path": img.path} for img in images]
    
    # Debug logging
    #app.logger.debug(f"Number of images fetched: {len(image_data)}")
    #for img in image_data:
    #    app.logger.debug(f"Image: {img}")

    return render_template('gallery.html', images=images)


@app.route('/messages/<image_id>')
def get_messages_html(image_id):
    stmt = sa.select(Message).where(Message.image_id == image_id).order_by(Message.timestamp.desc())
    messages = db.session.scalars(stmt).all()
    return render_template('messages_partial.html', messages=messages)


#@app.route('/api/images')
@app.route('/api/gallery-data')
def get_gallery_data():
#def get_images():
    stmt = sa.select(Image).order_by(Image.timestamp.desc())
    images = db.session.scalars(stmt).all()
    
    image_data = []
    for img in images:
        messages = [{"author": msg.author, "content": msg.content} for msg in img.messages]
        image_data.append({"id": img.id, "path": img.path, "messages": messages})
    
    #image_data = [{"id": img.id, "path": img.path} for img in images]
    
    return jsonify(image_data)

@app.route('/api/images')
def get_images():
    stmt = sa.select(Image).order_by(Image.timestamp.desc())
    images = db.session.scalars(stmt).all()
    return jsonify([{"id": img.id, "path": img.path} for img in images])

@app.route('/api/messages/<image_id>')
def get_messages(image_id):
    stmt = sa.select(Message).where(Message.image_id == image_id).order_by(Message.timestamp.desc())
    messages = db.session.scalars(stmt).all()
    return jsonify([{"author": msg.author, "content": msg.content} for msg in messages])





@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        #if 'file' not in request.files:
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            image_id = str(uuid.uuid4())
            relative_path = os.path.join(image_id, filename)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            file.save(full_path)

            new_image = Image(id=image_id, filename=filename, path=relative_path)
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
                relative_path = os.path.join(image_id, filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                file.save(full_path)

                new_image = Image(id=image_id, filename=filename, path=relative_path)
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

@app.route('/add_message/<image_id>', methods=['GET', 'POST'])
def add_message(image_id):
    stmt = sa.select(Image).where(Image.id == image_id)
    image = db.session.scalar(stmt)
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
        return redirect(url_for('add_message', image_id=image_id))
    
    # Fetch messages for this image
    message_stmt = sa.select(Message).where(Message.image_id == image_id).order_by(Message.timestamp.desc())
    messages = db.session.scalars(message_stmt).all()

    return render_template('add_message.html', image=image, messages=messages)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'reset-db':
        with app.app_context():
            db.drop_all()
            db.create_all()
            print("All tables dropped and recreated successfully!")
    else:
        with app.app_context():
            db.create_all()
            print("All tables created successfully!")
        app.run(host='0.0.0.0', port=3000)