from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user, login_required
from app import db, socketio
from app.models import User, Message, Group, GroupMember
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))
    return render_template('index.html')

@main_bp.route('/chat')
@login_required
def chat():
    users = User.query.filter(User.id != current_user.id).all()
    groups = current_user.groups
    return render_template('chat.html', users=users, groups=groups)

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@main_bp.route('/create_group', methods=['POST'])
@login_required
def create_group():
    group_name = request.form.get('group_name')
    if group_name:
        new_group = Group(name=group_name)
        db.session.add(new_group)
        db.session.commit()
        
        # Add creator to group
        membership = GroupMember(user_id=current_user.id, group_id=new_group.id)
        db.session.add(membership)
        db.session.commit()
        
        flash('Group created successfully!', 'success')
    return redirect(url_for('main.chat'))

@main_bp.route('/add_to_group/<int:group_id>', methods=['POST'])
@login_required
def add_to_group(group_id):
    user_id = request.form.get('user_id')
    group = Group.query.get_or_404(group_id)
    
    if current_user.id not in [member.user_id for member in group.members]:
        flash('You are not a member of this group!', 'danger')
        return redirect(url_for('main.chat'))
    
    if user_id:
        # Check if user is already in group
        existing_member = GroupMember.query.filter_by(
            user_id=user_id, group_id=group_id).first()
        if not existing_member:
            membership = GroupMember(user_id=user_id, group_id=group_id)
            db.session.add(membership)
            db.session.commit()
            flash('User added to group!', 'success')
        else:
            flash('User is already in the group!', 'warning')
    
    return redirect(url_for('main.chat'))

@socketio.on('private_message')
def handle_private_message(data):
    sender_id = current_user.id
    recipient_id = data['recipient_id']
    content = data['content']
    
    message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content
    )
    db.session.add(message)
    db.session.commit()
    
    socketio.emit('new_private_message', {
        'sender_id': sender_id,
        'sender_name': current_user.username,
        'content': content,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'user_{recipient_id}')

@socketio.on('group_message')
def handle_group_message(data):
    sender_id = current_user.id
    group_id = data['group_id']
    content = data['content']
    
    message = Message(
        sender_id=sender_id,
        group_id=group_id,
        content=content
    )
    db.session.add(message)
    db.session.commit()
    
    group = Group.query.get(group_id)
    for member in group.members:
        if member.user_id != sender_id:
            socketio.emit('new_group_message', {
                'group_id': group_id,
                'sender_id': sender_id,
                'sender_name': current_user.username,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{member.user_id}')

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        socketio.emit('user_status', {
            'user_id': current_user.id,
            'status': 'online'
        }, broadcast=True)
        socketio.emit('join_room', {'room': f'user_{current_user.id}'})

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        socketio.emit('user_status', {
            'user_id': current_user.id,
            'status': 'offline'
        }, broadcast=True)