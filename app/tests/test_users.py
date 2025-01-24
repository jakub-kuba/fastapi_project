# import sys
# import os

# sys.path.append(
#     os.path.abspath(
#         os.path.join(os.path.dirname(__file__), "../../")
#     )
# )

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.models import User, Proposals, Base


@pytest.fixture(scope="module")
def setup_database():
    """Fixture to set up the in-memory SQLite database and session."""
    # Create an in-memory SQLite database
    engine = create_engine('sqlite:///:memory:')

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create tables
    Base.metadata.create_all(engine)

    # Create a session factory
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session  # Provide the session to tests

    # Clean up after tests
    session.close()
    engine.dispose()


def test_create_user(setup_database):
    """Test the creation of a user."""
    session = setup_database

    # Create a test user
    new_user = User(username="testuser",
                    email="testuser@example.com", password="securepassword")
    session.add(new_user)
    session.commit()

    # Retrieve the user from the database
    saved_user = session.query(User).filter_by(username="testuser").first()

    assert saved_user is not None
    assert saved_user.username == "testuser"
    assert saved_user.email == "testuser@example.com"


def test_create_proposal(setup_database):
    """Test the creation of a proposal."""
    session = setup_database

    # Create a test user
    new_user = User(username="testuser2",
                    email="testuser2@example.com", password="securepassword")
    session.add(new_user)
    session.commit()

    # Create a proposal for the user
    new_proposal = Proposals(user_id=new_user.id, title="Test Proposal",
                             composer="Test Composer", info="Some info")
    session.add(new_proposal)
    session.commit()

    # Retrieve the proposal from the database
    saved_proposal = session.query(Proposals).filter_by(
        title="Test Proposal").first()

    assert saved_proposal is not None
    assert saved_proposal.title == "Test Proposal"
    assert saved_proposal.composer == "Test Composer"
    assert saved_proposal.user_id == new_user.id


def test_relationship_between_user_and_proposal(setup_database):
    """Test the relationship between a user and a proposal."""
    session = setup_database

    # Create a test user
    new_user = User(username="testuser3",
                    email="testuser3@example.com", password="securepassword")
    session.add(new_user)
    session.commit()

    # Create a proposal for the user
    new_proposal = Proposals(
        user_id=new_user.id,
        title="Proposal for Relationship Test",
        composer="Composer X",
        info="Info X"
    )
    session.add(new_proposal)
    session.commit()

    # Retrieve the user and their proposal
    saved_user = session.query(User).filter_by(username="testuser3").first()
    saved_proposal = session.query(Proposals).filter_by(
        title="Proposal for Relationship Test").first()

    assert saved_user is not None
    assert saved_proposal is not None
    assert saved_proposal.user_id == saved_user.id
