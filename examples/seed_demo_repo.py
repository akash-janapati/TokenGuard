"""Generate a deterministic demo repository for the P2 token-reduction demo.

Run:  python examples/seed_demo_repo.py
Creates: examples/frozen_repo/
"""

from __future__ import annotations

import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "frozen_repo")

CORE_FILES = {
    "src/auth/login.ts": '''import { validateCredentials } from "./auth";
import { findUserByEmail } from "../services/userService";
import { createSession } from "./session";
import { User } from "../models/user";

// Entry point for the login flow: lookup the user, validate credentials,
// then open a session and return its token.
export async function login(email: string, password: string): Promise<string> {
  const user = await findUserByEmail(email);
  if (!user) {
    throw new Error("User not found");
  }
  const valid = await validateCredentials(user, password);
  if (!valid) {
    throw new Error("Invalid password");
  }
  const session = await createSession(user);
  return session.token;
}

export async function logout(token: string): Promise<void> {
  const session = await getSession(token);
  if (session) {
    await destroySession(session);
  }
}
''',
    "src/auth/auth.ts": '''import { User } from "../models/user";
import { verifyPassword } from "../utils/validate";

// DEMO SECRET - intentionally fake, exercises the redaction path.
export const API_KEY = "sk-abcdef0123456789abcdef0123456789";

// Credential validation for the login flow.
export async function validateCredentials(user: User, password: string): Promise<boolean> {
  if (!user.passwordHash) {
    return false;
  }
  return verifyPassword(password, user.passwordHash);
}

export function isAuthorized(token: string): boolean {
  return Boolean(token) && token.length > 12;
}
''',
    "src/auth/session.ts": '''import { User } from "../models/user";

export interface Session {
  token: string;
  userId: string;
  expiresAt: number;
}

const SESSION_TTL_MS = 1000 * 60 * 60 * 24;

// Create an authenticated session for a user after a successful login.
export async function createSession(user: User): Promise<Session> {
  const token = `${user.id}.${Date.now()}.${Math.random().toString(36).slice(2)}`;
  return {
    token,
    userId: user.id,
    expiresAt: Date.now() + SESSION_TTL_MS,
  };
}

export async function getSession(token: string): Promise<Session | null> {
  return sessionStore.get(token) ?? null;
}

export async function destroySession(session: Session): Promise<void> {
  sessionStore.delete(session.token);
}

const sessionStore = new Map<string, Session>();
''',
    "src/services/userService.ts": '''import { User } from "../models/user";
import { hashPassword } from "../utils/validate";

// In-memory user store used by the login flow.
const users = new Map<string, User>();

export async function findUserByEmail(email: string): Promise<User | null> {
  for (const user of users.values()) {
    if (user.email.toLowerCase() === email.toLowerCase()) {
      return user;
    }
  }
  return null;
}

export async function createUser(email: string, password: string): Promise<User> {
  const user: User = {
    id: String(users.size + 1),
    email,
    passwordHash: await hashPassword(password),
    createdAt: Date.now(),
  };
  users.set(user.id, user);
  return user;
}

export async function getUserById(id: string): Promise<User | null> {
  return users.get(id) ?? null;
}
''',
    "src/models/user.ts": '''export interface User {
  id: string;
  email: string;
  passwordHash: string;
  createdAt: number;
}

export interface PublicUser {
  id: string;
  email: string;
}
''',
    "src/utils/validate.ts": '''export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  const computed = await hashPassword(plain);
  return computed === hash;
}

export async function hashPassword(plain: string): Promise<string> {
  let h = 0;
  for (let i = 0; i < plain.length; i += 1) {
    h = (h * 31 + plain.charCodeAt(i)) | 0;
  }
  return `h${h}`;
}

export function validateEmail(email: string): boolean {
  return /^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email);
}
''',
}

FILLER_TEMPLATES = [
    ("format", "formatLabel", "const {0} = (input: string): string => {{ return input.trim(); }};"),
    ("parse", "parseNumber", "export function {0}(value: string): number {{ return Number(value) || 0; }}"),
    ("string", "capitalize", "export function {0}(value: string): string {{ return value.charAt(0).toUpperCase() + value.slice(1); }}"),
    ("array", "chunkItems", "export function {0}<T>(items: T[], size: number): T[][] {{ const out: T[][] = []; for (let i = 0; i < items.length; i += size) {{ out.push(items.slice(i, i + size)); }} return out; }}"),
    ("date", "addDays", "export function {0}(date: Date, days: number): Date {{ return new Date(date.getTime() + days * 86400000); }}"),
    ("math", "clamp", "export function {0}(value: number, min: number, max: number): number {{ return Math.min(Math.max(value, min), max); }}"),
]


def _filler(index: int) -> tuple:
    category, fn, body = FILLER_TEMPLATES[index % len(FILLER_TEMPLATES)]
    name = f"{fn}{index}"
    lines = [
        f"// Auto-generated utility #{index} ({category}).",
        "// Kept intentionally generic to act as repository noise.",
        "",
        body.format(name),
        "",
        f"export const {category.upper()}_{index}_LIMIT = {index * 10};",
        "",
    ]
    path = f"src/utils/{category}_{index}.ts"
    return path, "\n".join(lines)


def build_files() -> dict:
    files = dict(CORE_FILES)
    for i in range(1, 25):
        path, content = _filler(i)
        files[path] = content
    files["package.json"] = (
        '{\n  "name": "frozen-demo-repo",\n  "version": "1.0.0",\n'
        '  "private": true\n}\n'
    )
    files["README.md"] = "# Frozen Demo Repo\n\nSample app used for the LocalPilot token-reduction demo.\n"
    files["node_modules/lodash/index.js"] = (
        "// vendored dependency that must be excluded from context\n"
        + "module.exports = {}\n" * 200
    )
    files["dist/bundle.js"] = "// generated build artifact\n" + "console.log(0);\n" * 300
    return files


def main() -> None:
    if os.path.isdir(REPO):
        shutil.rmtree(REPO)
    for rel, content in build_files().items():
        full = os.path.join(REPO, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
    print(f"Seeded demo repo at {REPO}")


if __name__ == "__main__":
    main()
