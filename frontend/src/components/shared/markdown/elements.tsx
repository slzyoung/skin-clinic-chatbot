import React from "react";
import { RiImageLine } from "@remixicon/react";
import type { Components } from "react-markdown";
import { extractNodeText, isValidImageUrl, resolveImageUrl } from "./utils";

export const defaultMarkdownComponents: Components = {
	img: ({ src, alt, ...props }) => {
		const strSrc = typeof src === "string" ? src.trim() : "";
		if (!isValidImageUrl(strSrc)) {
			return null;
		}

		const resolvedSrc = resolveImageUrl(strSrc);

		return (
			<span className="my-1.5 inline-flex flex-col max-w-full rounded-lg border border-zinc-200 bg-zinc-50/50 overflow-hidden align-top min-w-16 min-h-16">
				{/* eslint-disable-next-line @next/next/no-img-element */}
				<img
					src={resolvedSrc}
					alt={typeof alt === "string" ? alt : "Document Image"}
					className="max-h-60 sm:max-h-64 w-auto max-w-full object-contain cursor-pointer transition hover:opacity-90 block"
					loading="lazy"
					onClick={() => {
						if (resolvedSrc) {
							window.open(resolvedSrc, "_blank", "noopener,noreferrer");
						}
					}}
					onError={(e) => {
						e.currentTarget.style.display = "none";
						const fallback = e.currentTarget.nextElementSibling as HTMLElement;
						if (fallback) fallback.style.display = "flex";
					}}
					{...props}
				/>
				<span
					style={{ display: "none" }}
					className="size-16 sm:size-20 bg-zinc-100 items-center justify-center text-zinc-400 text-xs flex-col p-1 text-center select-none"
				>
					<RiImageLine className="size-4 text-zinc-400 mb-0.5" />
					<span className="text-xs text-zinc-400 font-medium">N/A</span>
				</span>
				{alt && typeof alt === "string" && (
					<span className="block px-2.5 py-1 text-xs text-zinc-600 font-normal bg-white border-t border-zinc-100 truncate max-w-full">
						{alt}
					</span>
				)}
			</span>
		);
	},
	blockquote: ({ children }) => {
		const textContent = extractNodeText(children).trim();

		const isDanger = /kontraindikasi|danger|forbid|bahaya/i.test(textContent);
		const isWarning = /perhatian|warning|caution|hati-hati|peringatan/i.test(textContent);
		const isSuccess = /success|rekomendasi|anjuran/i.test(textContent);

		let borderClass = "border-l-2 border-blue-600 bg-blue-50/40 text-zinc-900";

		if (isDanger) {
			borderClass = "border-l-2 border-red-600 bg-red-50/50 text-red-950";
		} else if (isWarning) {
			borderClass = "border-l-2 border-amber-600 bg-amber-50/50 text-amber-950";
		} else if (isSuccess) {
			borderClass = "border-l-2 border-emerald-600 bg-emerald-50/50 text-emerald-950";
		}

		return (
			<div
				className={`my-1.5 py-1.5 px-3 rounded-r-md ${borderClass} text-xs sm:text-sm leading-normal shadow-none [&>p]:m-0`}
			>
				{children}
			</div>
		);
	},
	p: ({ children }) => {
		const text = extractNodeText(children).trim();
		const isFAQMatch = text.match(/^\*\*Q:\s*([^*]+)\*\*\s*(?:\n+|:)?\s*(?:\*\*A:\s*)?(.+)$/i);
		if (isFAQMatch) {
			const question = isFAQMatch[1].trim();
			const answer = isFAQMatch[2].trim();
			return (
				<details className="my-2 p-2.5 rounded-md border border-zinc-200 bg-white group [&_summary::-webkit-details-marker]:hidden">
					<summary className="cursor-pointer text-sm font-medium text-zinc-900 flex items-center justify-between gap-2 list-none select-none">
						<span className="flex items-center gap-2">
							<span className="text-xs font-semibold text-zinc-700 bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200">
								Q
							</span>
							<span>{question}</span>
						</span>
						<span className="text-zinc-400 text-xs font-mono transition-transform group-open:rotate-180">
							▾
						</span>
					</summary>
					<div className="pt-2 pl-7 text-xs sm:text-sm text-zinc-700 leading-normal border-t border-zinc-100 mt-2">
						{answer}
					</div>
				</details>
			);
		}
		return <p className="my-1 text-sm text-zinc-900 leading-normal font-normal">{children}</p>;
	},
	ol: ({ children }) => (
		<ol className="list-decimal pl-5 my-1 space-y-0.5 text-sm text-zinc-900 leading-normal font-normal marker:text-zinc-600">
			{children}
		</ol>
	),
	ul: ({ children }) => (
		<ul className="list-disc pl-5 my-1 space-y-0.5 text-sm text-zinc-900 leading-normal font-normal marker:text-zinc-500">
			{children}
		</ul>
	),
	li: ({ children }) => (
		<li className="text-sm leading-normal text-zinc-900 font-normal">{children}</li>
	),
	h1: ({ children }) => (
		<h1 className="text-base font-semibold text-zinc-950 first:mt-1 mt-4 mb-2 tracking-tight">
			{children}
		</h1>
	),
	h2: ({ children }) => (
		<h2 className="text-sm sm:text-base font-semibold text-zinc-950 first:mt-1 mt-4 mb-1.5 flex items-center gap-2 tracking-tight">
			{children}
		</h2>
	),
	h3: ({ children }) => {
		const text = extractNodeText(children).trim();
		const isContra = /kontraindikasi/i.test(text);
		const isPreCare = /pre-care|persiapan/i.test(text);
		const isAfterCare = /aftercare|setelah/i.test(text);

		return (
			<h3
				className={`text-sm font-semibold mt-2.5 mb-1 flex items-center gap-1.5 ${
					isContra
						? "text-red-900"
						: isPreCare
							? "text-blue-900"
							: isAfterCare
								? "text-emerald-900"
								: "text-zinc-900"
				}`}
			>
				{children}
			</h3>
		);
	},
	strong: ({ children }) => <strong className="font-semibold text-zinc-950">{children}</strong>,
	hr: () => <div className="my-2 border-t border-zinc-100" />,
	table: ({ children }) => (
		<div className="my-2 overflow-x-auto rounded-md border border-zinc-200 bg-white">
			<table className="w-full text-left text-xs sm:text-sm border-collapse divide-y divide-zinc-200">
				{children}
			</table>
		</div>
	),
	thead: ({ children }) => (
		<thead className="bg-zinc-50 text-zinc-900 font-semibold">{children}</thead>
	),
	tbody: ({ children }) => <tbody className="divide-y divide-zinc-100 bg-white">{children}</tbody>,
	tr: ({ children }) => <tr className="hover:bg-zinc-50/60 transition-colors">{children}</tr>,
	th: ({ children }) => <th className="px-3 py-1.5 font-semibold text-zinc-900">{children}</th>,
	td: ({ children }) => <td className="px-3 py-1.5 text-zinc-800 font-normal">{children}</td>,
	code: ({ children, className }) => {
		const isInline = !className || !className.includes("language-");
		if (isInline) {
			return (
				<code className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-800 font-mono text-xs border border-zinc-200/80">
					{children}
				</code>
			);
		}
		return <code className={className}>{children}</code>;
	},
	pre: ({ children }) => (
		<pre className="my-2 p-3 rounded-lg bg-zinc-900 text-zinc-100 text-xs font-mono overflow-x-auto">
			{children}
		</pre>
	),
};
