from flask import Flask, abort, request
import secrets
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ethereum.utils import ecrecover_to_pub, sha3
from eth_utils.hexidecimal import encode_hex, decode_hex, add_0x_prefix

app = Flask(__name__)

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
    confirmed = Column(Boolean)
    challenge = Column(String)

def create_all():
    Base.metadata.create_all(engine)

@app.route("/")
def root():
    return "GET /reveal/&lt;address&gt; to return the identity string of an address, or 404 if address is unknown.<br> \
            POST /register to begin the process of creating a registration. A challenge will be issued.<br> \
            address: &lt;address&gt; <br>\
            identity: &lt;identity&gt; <br>\
            POST /confirm to submit a signed challenge, the final step of registration.\
            address: &lt;address&gt; <br> \
            challenge: &lt;challenge&gt; <br> \
            message_hash: &lt;message_hash&gt; <br> \
            signature: &lt;signature&gt;"

@app.route("/reveal/<address>")
def get_identity(address):
    identity = session.query(identities).filter_by(address=address).filter_by(confirmed=True).first()
    if not identity:
        abort(404)
    return identity.identity

@app.route("/register", methods=['POST'])
def begin_registry():
    if 'address' not in request.form or 'identity' not in request.form:
        abort(400)

    address = request.form['address']
    identity = request.form['identity']

    challenge = secrets.token_hex(30)

    identity = Identity(address=address, identity=identity, confirmed=False, challenge=challenge)
    session.add(identity)
    session.commit()

    return challenge

@app.route("/confirm", methods=['POST'])
def confirm_identity():
    required = ['address', 'challenge', 'message_hash', 'signature']
    for field in required:
        if field not in request.form:
            abort(400)

    address = request.form['address']
    challenge = request.form['challenge']
    message_hash = request.form['message_hash']
    signature = request.form['signature']

    r = int(signature[0:66], 16)
    s = int(add_0x_prefix(signature[66:130]), 16)
    v = int(add_0x_prefix(signature[130:132]), 16)
    if v not in (27, 28):
        v += 27

    pubkey = ecrecover_to_pub(decode_hex(message_hash), v, r, s)
    if encode_hex(sha3(pubkey)[-20:]) == address:
        identity = session.query(identities).filter_by(address=address).filter_by(challenge=challenge).filter_by(confirmed=False).first()
        identity.confirmed = True
        session.commit()
    else:
        abort(403)

if __name__ == '__main__':
    app.run(debug=True)
