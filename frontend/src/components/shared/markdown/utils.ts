import React from "react";
import type { KeyValueItem } from "./types";

export function resolveImageUrl(src?: string | null): string {
	if (!src) return "";
	let trimmed = src.trim();

	// Normalize hallucinated `https://api/` or `http://api/` prefixes
	if (/^https?:\/\/api\//i.test(trimmed)) {
		trimmed = trimmed.replace(/^https?:\/\/api\//i, "/api/");
	}

	if (
		trimmed.startsWith("http://") ||
		trimmed.startsWith("https://") ||
		trimmed.startsWith("data:") ||
		trimmed.startsWith("blob:")
	) {
		return encodeURI(decodeURI(trimmed));
	}
	const backendBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(
		/\/api\/?$/,
		"",
	);
	const fullUrl = trimmed.startsWith("/") ? `${backendBase}${trimmed}` : `${backendBase}/${trimmed}`;
	return encodeURI(decodeURI(fullUrl));
}

export function isValidImageUrl(src?: string | null): boolean {
	if (!src) return false;
	const clean = src.trim().toLowerCase();
	if (
		!clean ||
		clean === "image_url" ||
		clean === "url" ||
		clean === "null" ||
		clean === "none" ||
		clean === "#" ||
		/new_image|placeholder|dummy|undefined|test_image|url_gambar|gambar_terlampir|url_/i.test(clean) ||
		clean.endsWith("/image_url") ||
		clean.endsWith("/url")
	) {
		return false;
	}
	return true;
}

export function parseBulletLines(text: string): KeyValueItem[] {
	const items: KeyValueItem[] = [];
	const lines = text.split("\n");
	for (const line of lines) {
		const match = line.match(/^[ \t]*[-*]\s*\*\*([^*]+)\*\*\s*[:–-]\s*(.+)$/);
		if (match) {
			const key = match[1].trim();
			const value = match[2].trim();
			if (
				value &&
				value.toLowerCase() !== "none" &&
				value.toLowerCase() !== "n/a" &&
				value.toLowerCase() !== "null"
			) {
				items.push({ key, value });
			}
		}
	}
	return items;
}

export function extractNodeText(node: React.ReactNode): string {
	if (!node) return "";
	if (typeof node === "string" || typeof node === "number") {
		return String(node);
	}
	if (Array.isArray(node)) {
		return node.map(extractNodeText).join(" ");
	}
	if (
		React.isValidElement(node) &&
		node.props &&
		(node.props as { children?: React.ReactNode }).children
	) {
		return extractNodeText((node.props as { children?: React.ReactNode }).children);
	}
	return "";
}

export function stripInternalMetadata(text?: string | null): string {
	if (!text) return "";
	// Normalize unencoded spaces in markdown image links ![alt](url) -> ![alt](encodedUrl)
	let cleaned = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, rawUrl) => {
		const trimmedUrl = rawUrl.trim();
		if (trimmedUrl.includes(" ")) {
			const encoded = trimmedUrl.replace(/ /g, "%20");
			return `![${alt}](${encoded})`;
		}
		return match;
	});

	// Normalize unicode bullet symbols (•, ●, ◦) to standard markdown list syntax
	cleaned = cleaned.replace(/^[ \t]*[•●◦][ \t]*/gm, "- ");

	return cleaned.trim();
}
