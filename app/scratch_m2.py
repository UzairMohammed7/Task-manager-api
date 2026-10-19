   from sqlalchemy import select

   from app.db.session import Base, SessionLocal, engine
   from app.models import Task, User

   Base.metadata.create_all(engine)

   with SessionLocal() as db:
       user = User(email="demo@example.com", hashed_password="not-a-real-hash")
       user.tasks.append(Task(title="Write M2 code"))
       db.add(user)
       db.commit()

       task = db.scalars(select(Task)).first()
       print(task, "| owner:", task.owner.email, "| priority:", task.priority.value)
       print("created_at:", task.created_at)