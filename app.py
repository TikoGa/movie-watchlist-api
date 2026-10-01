import os
import time

import psycopg
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Movie Watchlist API")


DATABASE_URL = (
    f"postgresql://"
    f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'db')}:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)


class Movie(BaseModel):
    title: str
    genre: str
    year: int
    watched: bool = False


def get_connection():
    return psycopg.connect(DATABASE_URL)


def create_table():
    for attempt in range(10):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS movies (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            genre VARCHAR(100) NOT NULL,
                            year INTEGER NOT NULL,
                            watched BOOLEAN NOT NULL DEFAULT FALSE
                        )
                        """
                    )
                conn.commit()

            print("Database is ready.")
            return

        except psycopg.OperationalError:
            print(f"Database not ready. Retry {attempt + 1}/10...")
            time.sleep(2)

    raise RuntimeError("Could not connect to PostgreSQL.")


@app.on_event("startup")
def startup():
    create_table()


@app.get("/")
def root():
    return {
        "message": "Welcome to Movie Watchlist API"
    }


@app.post("/movies")
def add_movie(movie: Movie):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO movies (title, genre, year, watched)
                VALUES (%s, %s, %s, %s)
                RETURNING id, title, genre, year, watched
                """,
                (
                    movie.title,
                    movie.genre,
                    movie.year,
                    movie.watched,
                ),
            )

            created_movie = cur.fetchone()

        conn.commit()

    return {
        "id": created_movie[0],
        "title": created_movie[1],
        "genre": created_movie[2],
        "year": created_movie[3],
        "watched": created_movie[4],
    }


@app.get("/movies")
def get_movies():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, genre, year, watched
                FROM movies
                ORDER BY id
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "genre": row[2],
            "year": row[3],
            "watched": row[4],
        }
        for row in rows
    ]
