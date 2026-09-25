"""Consistent online SQLite backup; never overwrite an existing backup."""
import os
from pathlib import Path
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'SQLite bazasining izchil zaxira nusxasini yaratish.'

    def add_arguments(self, parser):
        parser.add_argument('destination', type=Path)

    def handle(self, *args, **options):
        if connection.vendor != 'sqlite':
            raise CommandError('PostgreSQL uchun pg_dump ishlating.')
        target = options['destination']
        try:
            descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError as error:
            raise CommandError(str(error)) from error
        os.close(descriptor)
        try:
            connection.ensure_connection()
            with sqlite3.connect(target) as backup:
                connection.connection.backup(backup)
                if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('Zaxira nusxa yaxlitligi tekshiruvdan o‘tmadi.')
        except Exception:
            target.unlink(missing_ok=True)
            raise
        self.stdout.write(self.style.SUCCESS(f'Zaxira nusxa tayyor: {target}'))
