from flask import Flask, abort, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)
CORS(app)

db_uri = "sqlite:///identity.sqlite"
engine = create_engine(db_uri)

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

class Identity(Base):
    __tablename__ = 'identities'

    id = Column(Integer, primary_key=True)
    address = Column(String)
    identity = Column(String)

# Call from python3 shell to initialise db.
def create_all():
    Base.metadata.create_all(engine)

# Retreive an identity from an address.
@app.route("/<address>")
def get_identity(address):
    identity = session.query(Identity).filter_by(address=address).first()
    if not identity:
        abort(404)
    return jsonify({
        'address': identity.address,
        'identity': identity.identity
    })

# Register an identity to be associated with an address.
@app.route("/", methods=['POST'])
def begin_registry():
    if 'address' not in request.json or 'identity' not in request.json:
        abort(400)

    address = request.json['address']
    identity = request.json['identity']

    # Ensure address doesn't already have an identity associated.
    identity = session.query(Identity).filter_by(address=address).first()
    if identity is not None:
        abort(400)

    identity = Identity(address=address, identity=identity)
    session.add(identity)
    session.commit()

    return 'OK'

if __name__ == '__main__':
    app.run()
