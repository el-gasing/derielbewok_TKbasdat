from django.db import connection
from types import SimpleNamespace


def check_duplicate_claim(member, flight_number, ticket_number, flight_date, exclude_claim_id=None):
    normalized_ticket = (ticket_number or '').strip()

    sql = """
        SELECT c.id FROM auth_system_claimmissingmiles c
        JOIN auth_system_member m ON m.id = c.member_id
        JOIN auth_user u ON u.id = m.user_id
        WHERE LOWER(u.email) = LOWER(%s)
          AND UPPER(c.flight_number) = UPPER(%s)
          AND c.flight_date = %s
    """
    params = [member.user.email, flight_number, flight_date]

    if normalized_ticket:
        sql += " AND UPPER(COALESCE(c.ticket_number, '')) = UPPER(%s)"
        params.append(normalized_ticket)
    else:
        sql += " AND COALESCE(c.ticket_number, '') = ''"

    if exclude_claim_id is not None:
        sql += " AND c.id != %s"
        params.append(exclude_claim_id)

    sql += " LIMIT 1"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()

    return SimpleNamespace(id=row[0]) if row else None
