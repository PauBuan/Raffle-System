"""
app/models/group_repository.py
-------------------------------
Repository for _Groups and _GroupDepartments — SQLAlchemy ORM.
"""

from dataclasses import dataclass, field
from .database_manager import get_session
from .orm_models import Group as GroupORM, GroupDepartment as GroupDepartmentORM


@dataclass
class GroupInfo:
    group_id:         int
    group_name:       str
    building_tag:     str | None
    allocated_prizes: int
    status:           str = "NOT SET"
    departments:      list[str] = field(default_factory=list)


class GroupRepository:
    """CRUD operations for _Groups and _GroupDepartments tables."""

    def get_all_groups(self) -> list[GroupInfo]:
        """Return all groups with their department lists."""
        with get_session() as session:
            groups = session.query(GroupORM).order_by(GroupORM.GroupID).all()
            result = []
            for g in groups:
                depts = (
                    session.query(GroupDepartmentORM.Department)
                    .filter(GroupDepartmentORM.GroupID == g.GroupID)
                    .all()
                )
                result.append(GroupInfo(
                    group_id=g.GroupID,
                    group_name=g.GroupName,
                    building_tag=g.BuildingTag,
                    allocated_prizes=g.AllocatedPrizes or 0,
                    status=g.Status or "NOT SET",
                    departments=[d[0] for d in depts],
                ))
            return result

    def get_building_groups(self) -> dict[str, GroupInfo]:
        """Return groups with BuildingTag set, keyed by tag ('LTI', 'CIP')."""
        all_groups = self.get_all_groups()
        return {g.building_tag: g for g in all_groups if g.building_tag}

    def save_groups(self, groups: list[dict]) -> None:
        """
        Upsert groups and rebuild their department assignments.

        Each dict in *groups*:
            {
                'group_id': int | None,      # None = new group
                'group_name': str,
                'building_tag': str | None,
                'allocated_prizes': int,
                'departments': list[str],
            }
        """
        with get_session() as session:
            for g in groups:
                gid = g.get("group_id")

                if gid:
                    orm_group = session.query(GroupORM).get(gid)
                    if orm_group:
                        orm_group.GroupName = g["group_name"]
                        orm_group.BuildingTag = g.get("building_tag")
                        orm_group.AllocatedPrizes = g.get("allocated_prizes", 0)
                        orm_group.Status = "NOT SET"   # Auto-reset on edit
                    else:
                        orm_group = GroupORM(
                            GroupName=g["group_name"],
                            BuildingTag=g.get("building_tag"),
                            AllocatedPrizes=g.get("allocated_prizes", 0),
                        )
                        session.add(orm_group)
                        session.flush()
                        gid = orm_group.GroupID
                else:
                    orm_group = GroupORM(
                        GroupName=g["group_name"],
                        BuildingTag=g.get("building_tag"),
                        AllocatedPrizes=g.get("allocated_prizes", 0),
                    )
                    session.add(orm_group)
                    session.flush()
                    gid = orm_group.GroupID

                # Rebuild department assignments
                session.query(GroupDepartmentORM).filter(
                    GroupDepartmentORM.GroupID == gid
                ).delete()

                for dept in g.get("departments", []):
                    session.add(GroupDepartmentORM(GroupID=gid, Department=dept))

    def delete_group(self, group_id: int) -> None:
        """Delete a group and its department assignments."""
        with get_session() as session:
            session.query(GroupDepartmentORM).filter(
                GroupDepartmentORM.GroupID == group_id
            ).delete()
            session.query(GroupORM).filter(
                GroupORM.GroupID == group_id
            ).delete()

    def confirm_group_ready(self, group_id: int) -> None:
        """Set group status to READY FOR DRAWING."""
        with get_session() as session:
            group = session.query(GroupORM).get(group_id)
            if group:
                group.Status = "READY FOR DRAWING"

    def mark_group_not_set(self, group_id: int) -> None:
        """Reset group status to NOT SET (called after any edit)."""
        with get_session() as session:
            group = session.query(GroupORM).get(group_id)
            if group:
                group.Status = "NOT SET"

    def are_all_groups_ready(self) -> tuple[bool, list[str]]:
        """Check if all groups are READY FOR DRAWING.
        Returns (all_ready, list_of_not_ready_names)."""
        groups = self.get_all_groups()
        if not groups:
            return True, []
        not_ready = [g.group_name for g in groups if g.status != "READY FOR DRAWING"]
        return len(not_ready) == 0, not_ready
