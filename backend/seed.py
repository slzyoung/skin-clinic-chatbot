import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models.user import User, UserType, Role, UserRole
from app.core.security import get_password_hash
import app.models # Ensure all models are loaded

async def init_db():
    print("Connecting to database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    print("Creating tables...")
    async with engine.begin() as conn:
        # Create extension for pgvector and uuid
        await conn.execute(org_sql_text := __import__('sqlalchemy').text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.execute(org_sql_text := __import__('sqlalchemy').text('CREATE EXTENSION IF NOT EXISTS vector;'))
        
        # Tables are created via Alembic migrations now
        
    print("Seeding default user and roles...")
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Seed Roles
        for role_name in ["ADMIN", "FUNCTIONAL"]:
            result = await session.execute(__import__('sqlalchemy').select(Role).where(Role.name == role_name))
            if not result.scalar_one_or_none():
                session.add(Role(name=role_name))
        await session.commit()

        # Check if admin already exists
        result = await session.execute(__import__('sqlalchemy').select(User).where(User.email == 'admin@mail.com'))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            admin_user = User(
                email="admin@mail.com",
                name="System Administrator",
                type=UserType.STAFF,
                password_hash=get_password_hash("admin123")
            )
            session.add(admin_user)
            await session.commit()
            
            # Assign ADMIN role
            result = await session.execute(__import__('sqlalchemy').select(Role).where(Role.name == "ADMIN"))
            admin_role = result.scalar_one_or_none()
            if admin_role:
                session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
                await session.commit()
                
            print("Successfully seeded admin user: admin@mail.com / admin123")
        else:
            print("Admin user already exists.")
            
        # Seed Functional user
        result = await session.execute(__import__('sqlalchemy').select(User).where(User.email == 'dept@mail.com'))
        func_user = result.scalar_one_or_none()
        if not func_user:
            func_user = User(
                email="dept@mail.com",
                name="Functional Dept",
                type=UserType.STAFF,
                password_hash=get_password_hash("dept123")
            )
            session.add(func_user)
            await session.commit()
            
            result = await session.execute(__import__('sqlalchemy').select(Role).where(Role.name == "FUNCTIONAL"))
            func_role = result.scalar_one_or_none()
            if func_role:
                session.add(UserRole(user_id=func_user.id, role_id=func_role.id))
                await session.commit()
            print("Successfully seeded functional user: dept@mail.com / dept123")
            
        # Seed Doctor user
        result = await session.execute(__import__('sqlalchemy').select(User).where(User.email == 'doctor@mail.com'))
        doc_user = result.scalar_one_or_none()
        if not doc_user:
            doc_user = User(
                email="doctor@mail.com",
                name="Dr. Testing",
                type=UserType.DOCTOR,
                password_hash=get_password_hash("doctor123"),
                cis_id="DOC-TEST-01"
            )
            session.add(doc_user)
            await session.commit()
            print("Successfully seeded doctor user: doctor@mail.com / doctor123")

        # --- SEED MOCK DATA FOR FEATURES ---
        
        from app.models.branch import Branch, UserBranch
        from app.models.category import Category, UserCategory
        from app.models.knowledge import Knowledge, KnowledgeType, KnowledgeStatus, KnowledgeCategory
        from app.models.chat import ChatSession, ChatMessage, ChatStatus, ChatRole
        import uuid
        
        print("Seeding mock branches...")
        branch1_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        branch2_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        for b_id, name, address in [(branch1_id, "Jakarta Central Clinic", "Sudirman St. 12"), (branch2_id, "Bandung Main Clinic", "Sucipto St. 12")]:
            result = await session.execute(__import__('sqlalchemy').select(Branch).where(Branch.id == b_id))
            if not result.scalar_one_or_none():
                session.add(Branch(id=b_id, name=name, address=address, token_limit=50000))
        await session.commit()

        print("Seeding mock categories...")
        cat1_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        cat2_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        for c_id, name, desc in [(cat1_id, "Dermatology", "Skin diseases"), (cat2_id, "Skincare Routine", "Daily care")]:
            result = await session.execute(__import__('sqlalchemy').select(Category).where(Category.id == c_id))
            if not result.scalar_one_or_none():
                session.add(Category(id=c_id, name=name, description=desc))
        await session.commit()

        print("Linking doctor to branches and categories...")
        result = await session.execute(__import__('sqlalchemy').select(UserBranch).where(UserBranch.user_id == doc_user.id))
        if not result.scalars().first():
            session.add(UserBranch(user_id=doc_user.id, branch_id=branch1_id))
            session.add(UserCategory(user_id=doc_user.id, category_id=cat1_id))
            session.add(UserCategory(user_id=doc_user.id, category_id=cat2_id))
            await session.commit()

        print("Seeding mock knowledge...")
        result = await session.execute(__import__('sqlalchemy').select(Knowledge).where(Knowledge.title == "Acne Treatment Guidelines"))
        if not result.scalar_one_or_none():
            k = Knowledge(
                title="Acne Treatment Guidelines",
                type=KnowledgeType.PDF,
                file_name="acne_guidelines.pdf",
                original_path="/storage/acne_guidelines.pdf",
                status=KnowledgeStatus.APPROVED,
                uploaded_by=func_user.id,
                approved_by=admin_user.id
            )
            session.add(k)
            await session.commit()
            session.add(KnowledgeCategory(knowledge_id=k.id, category_id=cat1_id))
            await session.commit()

        print("Seeding mock chat session...")
        result = await session.execute(__import__('sqlalchemy').select(ChatSession).where(ChatSession.user_id == doc_user.id))
        if not result.scalars().first():
            cs = ChatSession(
                user_id=doc_user.id,
                branch_id=branch1_id,
                status=ChatStatus.ACTIVE,
                summary="Patient asking about acne treatment."
            )
            session.add(cs)
            await session.commit()
            
            session.add(ChatMessage(session_id=cs.id, role=ChatRole.USER, content="What is the standard treatment for severe acne?"))
            session.add(ChatMessage(session_id=cs.id, role=ChatRole.ASSISTANT, content="According to the Acne Treatment Guidelines, severe acne is usually treated with isotretinoin."))
            await session.commit()

    await engine.dispose()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(init_db())
