
import asyncio
import sqlite3
import time

from database import get_connection, initialize_database


TOKEN_LIMIT = 50_000
WINDOW_SECONDS = 60


class RateLimitExceeded(Exception):
    """Raised when a tenant exceeds the token limit."""


class TokenRateLimiter:
    def __init__(
        self,
        token_limit=TOKEN_LIMIT,
        window_seconds=WINDOW_SECONDS,
    ):
        if token_limit <= 0 or window_seconds <= 0:
            raise ValueError("Limits must be positive")

        self.token_limit = token_limit
        self.window_seconds = window_seconds
        initialize_database()

    def _reserve_sync(self, tenant_key, tokens):
        if not isinstance(tenant_key, str) or not tenant_key:
            raise ValueError("A tenant API key is required")

        if type(tokens) is not int or tokens <= 0:
            raise ValueError("Tokens must be a positive integer")

        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")

            now = time.time()
            cutoff = now - self.window_seconds

            connection.execute(
                "DELETE FROM token_usage WHERE timestamp <= ?",
                (cutoff,),
            )

            row = connection.execute(
                """
                SELECT COALESCE(SUM(tokens), 0)
                FROM token_usage
                WHERE tenant_key = ? AND timestamp > ?
                """,
                (tenant_key, cutoff),
            ).fetchone()

            used_tokens = row[0]

            if used_tokens + tokens > self.token_limit:
                raise RateLimitExceeded(
                    "Tenant token rate limit exceeded"
                )

            cursor = connection.execute(
                """
                INSERT INTO token_usage (
                    tenant_key,
                    tokens,
                    timestamp
                )
                VALUES (?, ?, ?)
                """,
                (tenant_key, tokens, now),
            )

            reservation_id = cursor.lastrowid
            connection.commit()

            return {
                "reservation_id": reservation_id,
                "tenant_key": tenant_key,
                "used_tokens": used_tokens + tokens,
                "remaining_tokens": (
                    self.token_limit - used_tokens - tokens
                ),
            }

    async def reserve(self, tenant_key, tokens):
        return await asyncio.to_thread(
            self._reserve_sync,
            tenant_key,
            tokens,
        )

    def _refund_sync(self, reservation_id, tenant_key):
        if type(reservation_id) is not int or reservation_id <= 0:
            raise ValueError("Invalid reservation ID")

        if not isinstance(tenant_key, str) or not tenant_key:
            raise ValueError("A tenant API key is required")

        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")

            cursor = connection.execute(
                """
                DELETE FROM token_usage
                WHERE id = ? AND tenant_key = ?
                """,
                (reservation_id, tenant_key),
            )

            refunded = cursor.rowcount == 1
            connection.commit()

            return refunded

    async def refund(self, reservation_id, tenant_key):
        return await asyncio.to_thread(
            self._refund_sync,
            reservation_id,
            tenant_key,
        )


if __name__ == "__main__":
    async def main():
        limiter = TokenRateLimiter()
        tenant = "step108_demo_tenant"

        try:
            reservation = await limiter.reserve(tenant, 100)

            print("Reservation successful")
            print(reservation)

            refunded = await limiter.refund(
                reservation["reservation_id"],
                tenant,
            )

            print("Refund successful:", refunded)

        except RateLimitExceeded as error:
            print(f"Rate limit reached: {error}")

        except sqlite3.Error:
            print("SQLite database operation failed")

    asyncio.run(main())
