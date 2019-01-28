from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand
from app import create_app
from app import db

app = create_app('production')
manage = Manager(app)
migrate = Migrate(app,db)
manage.add_command('db',MigrateCommand)

if __name__ == '__main__':
    manage.run()
