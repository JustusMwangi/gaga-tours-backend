"""File repository — data access for the File model."""

from datetime import datetime, timezone

from app.blueprints.files.models import File


class FileRepository:
    """Data access for the File model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, file_id):
        """Get file by ID."""
        return self.session.get(File, file_id)

    def find_active_by_id(self, file_id):
        """Get non-deleted file."""
        return (
            self.session.query(File)
            .filter(
                File.id == file_id,
                File.deleted_at.is_(None),
            )
            .first()
        )

    def list_files(self, page=1, per_page=20, search=None, mime_type=None):
        """Paginated file list.

        Returns (files, total) tuple.
        """
        query = self.session.query(File).filter(
            File.deleted_at.is_(None),
        )

        if search:
            pattern = f"%{search}%"
            query = query.filter(File.original_filename.ilike(pattern))

        if mime_type:
            query = query.filter(File.mime_type == mime_type)

        total = query.count()

        files = (
            query.order_by(File.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return files, total

    def create(self, file_obj):
        """Add + flush."""
        self.session.add(file_obj)
        self.session.flush()
        return file_obj

    def soft_delete(self, file_obj):
        """Set deleted_at."""
        file_obj.deleted_at = datetime.now(timezone.utc)
        self.session.flush()

    def hard_delete(self, file_obj):
        """Permanent delete from database — for cleanup tasks."""
        self.session.delete(file_obj)
        self.session.flush()
