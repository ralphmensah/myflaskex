from peewee import CharField, DateTimeField, Model,SqliteDatabase,ForeignKeyField,TextField,IntegerField,DoesNotExist, MySQLDatabase,fn
from flask_login import UserMixin,LoginManager, current_user
from playhouse.sqliteq import SqliteQueueDatabase # peewee extra lib playhouse
import arrow # time and date 
from .auth.utils import Relationship_status as rstatus
from datetime import datetime as dtime
import os 
from flask import abort

login_manager = LoginManager()

# sqlite database file path
db_path = os.path.join(os.path.dirname(__file__) + '/auth/database/blogDB.db')

# peeweee sqlite database config
# db = SqliteDatabase(db_path, pragmas = {'foreign_keys' : 1,'cache_size': 1024,'journal_mode': 'wal'})
db = MySQLDatabase(database='mydb',user = 'admin',password='cybertron')
# all table base 
class BaseModel(Model):
    
    class Meta:
        database = db


class User(BaseModel,UserMixin):
	name = CharField()
	email = CharField(unique = True)
	username = CharField(unique = True)
	password = CharField()
	lastseen = CharField(default=dtime.now())
	photo = CharField(default='photo.jpg')
	joined = DateTimeField(default=dtime.now())

	
	def dtime(self):
		utc = arrow.get(self.joined)
		return utc.humanize()

	def count_user_post(self):
		return Post.user_post().count()

class Post(BaseModel):
	content = TextField()
	date = DateTimeField(default = dtime.now())
	user = ForeignKeyField(User, backref='user_post', on_delete='cascade', on_update='cascade')
	likes = CharField(default= 0)

	def __unicode__(self):
		return self.content
	@classmethod
	def dtime(cls,date):
		utc = arrow.get(date)
		return utc.humanize()

	@classmethod
	def user_post(cls):
		# .where(Post.user == current_user.id)
		return Post.select().order_by(Post.date.desc())

	@classmethod
	def delete_post(cls,pid):
		if Post.select().where(Post.id == pid):
			return Post.delete().where(Post.id == pid).execute()
	@classmethod
	def is_post_liked(self,pid,user):
		return (LikePost.select().where((LikePost.post == pid) & (LikePost.user == user)).exists())

	@classmethod
	def like_post(cls,pid,user):
		if not Post.is_post_liked(pid,user):
			post = Post.get(Post.id == pid)
			LikePost.create(post=pid, user = user)
			Post.update(likes  = int(post.likes) + 1).where((Post.id == post.id) & (Post.user == post.user)).execute()

	@classmethod
	def unlike_post(cls,pid,user):
		if Post.is_post_liked(pid,user):
			post = Post.get(Post.id == pid)
			Post.update(likes = int(post.likes) - 1).where((Post.id == post.id) & (Post.user == post.user)).execute()

class LikePost(BaseModel):
	post = ForeignKeyField(Post, backref='post_like', on_delete='cascade', on_update='cascade')
	user = ForeignKeyField(User, backref='like_user', on_delete='cascade', on_update='cascade')
	date = DateTimeField(default = dtime.now())

	@classmethod
	def delete_like(cls,pid,user):
		return cls.delete().where((cls.post == pid) & (cls.user == user)).execute()

class Comment(BaseModel):
	content = TextField()
	post = ForeignKeyField(Post, backref='post_comment', on_delete='cascade', on_update='cascade')
	date = DateTimeField(default = dtime.now())
	user = ForeignKeyField(User, backref='comment_user', on_delete='cascade', on_update='cascade')
	likes = CharField(default= 0)

class relationship(BaseModel):
	from_user = ForeignKeyField(User, backref='rel_user', on_delete='cascade', on_update='cascade')
	to_user = ForeignKeyField(User, backref='rel_user', on_delete='cascade', on_update='cascade')
	status = IntegerField(default = rstatus.pending)
	action_user = ForeignKeyField(User, backref='rel_user', on_delete='cascade', on_update='cascade')
	date = DateTimeField(default=dtime.now())

	@classmethod
	def is_to_follow_pending(cls,to_user,from_user):
		return (cls.select().where((cls.to_user == to_user) & (cls.from_user == from_user)  & (cls.status == rstatus.pending)))

	@classmethod
	def is_from_follow_pending(cls,to_user,from_user):
		return (cls.select().where((cls.to_user == to_user) & (cls.from_user == from_user)  & (cls.status == rstatus.pending)))

	@classmethod
	def pending_followers(cls,to_user):
		return (cls.select().where((cls.to_user == to_user)  & (cls.status == rstatus.pending)))

	@classmethod
	def follow(cls,from_user,to_user):
		if not cls.is_from_follow_pending(to_user,from_user) or not cls.is_to_follow_pending(to_user,from_user):
			return (relationship.create(from_user = from_user,to_user = to_user, action_user = from_user))
	@classmethod
	def cancel_relationship(cls,action_user, to_user):
		return cls.update(status = rstatus.cancel).where((cls.action_user == action_user) & (cls.to_user == to_user)).execute()

	@classmethod
	def delete_pending_relationship(cls,action_user, to_user):
		return cls.update(status = rstatus.delete).where((cls.action_user == action_user) & (cls.to_user == to_user)).execute()

	@classmethod
	def accept_relationship(cls,from_user, to_user):
		return cls.update(status = rstatus.accept).where((cls.from_user == from_user) & (cls.to_user == to_user)).execute()

	@classmethod
	def is_related(cls,to_user,from_user):
		return (cls.select().where((cls.to_user == to_user) & (cls.from_user == from_user)  & (cls.status == rstatus.accept)).exists())

db.connect()
db.create_tables([User,LikePost,Post,relationship])
db.close()

@login_manager.user_loader
def load_user(user_id):
	return User.get_by_id(user_id)