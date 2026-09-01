import { RiStethoscopeLine, RiZoomInLine } from "@remixicon/react";
import React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

export function resolveImageUrl(src?: string | null): string {
	if (!src) return "";
	const trimmed = src.trim();
	if (
		trimmed.startsWith("http://") ||
		trimmed.startsWith("https://") ||
		trimmed.startsWith("data:") ||
		trimmed.startsWith("blob:")
	) {
		return trimmed;
	}
	const backendBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(
		/\/api\/?$/,
		"",
	);
	return trimmed.startsWith("/") ? `${backendBase}${trimmed}` : `${backendBase}/${trimmed}`;
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
		clean.endsWith("/image_url") ||
		clean.endsWith("/url")
	) {
		return false;
	}
	return true;
}

interface KeyValueItem {
	key: string;
	value: string;
}

interface CardData {
	imageUrl?: string;
	imageAlt?: string;
	items: KeyValueItem[];
}

function parseBulletLines(text: string): KeyValueItem[] {
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

interface Segment {
	type: "markdown" | "product-card" | "treatment-card" | "regimen-card" | "dos-donts-card";
	content: string;
	data?: CardData;
	extraData?: Record<string, unknown>;
}

function parseMarkdownSegments(markdown: string): Segment[] {
	if (!markdown) return [];

	// Pattern 1: Product or Treatment Overview Cards
	const cardPattern =
		/(?:!\[([^\]]*)\]\(([^)]+)\)\s*\n+)?###\s*(Product\s+(?:Overview|Details|Info|Specification|Summary)|Overview\s+Produk|Spesifikasi\s+Produk|Info\s+Produk|Ringkasan\s+Produk|Detail\s+Produk|Treatment\s+(?:Overview|Details|Info|Procedure|Summary)|Overview\s+Tindakan|Prosedur\s+Klinis|Detail\s+Tindakan|Prosedur\s+Medis|Protokol\s+Perawatan|Info\s+Tindakan)\s*\n+(?:!\[([^\]]*)\]\(([^)]+)\)\s*\n+)?((?:[ \t]*[-*]\s*\*\*[^*]+\*\*\s*[:–-][^\n]+(?:\n|$))+)/gi;

	// Pattern 2: Skincare Regimen / Rutinitas Routine Card
	const regimenPattern =
		/###\s*(?:Cara\s+Penggunaan|Rutinitas|Aturan\s+Pakai|Skincare\s+Routine|Daily\s+Routine|Waktu\s+Pemakaian)\s*\n+((?:[ \t]*[-*]\s*\*\*(?:Pagi|Siang|Malam|Morning|Night|Evening|Sore)\*\*\s*[:–-][^\n]+(?:\n|$))+)/gi;

	// Pattern 3: Do's & Don'ts Comparison Card
	const dosDontsPattern =
		/###\s*(?:Anjuran\s+&\s+Larangan|Do's\s+&\s+Don'ts|Do's\s+and\s+Don'ts|Yang\s+Boleh\s+&\s+Dilarang|Instruksi\s+Pasien)\s*\n+((?:[ \t]*[-*]\s*\*\*(?:Do's?|Anjuran|Boleh|Disarankan|Don'ts?|Larangan|Dilarang|Tidak\s+Boleh)\*\*\s*[:–-][^\n]+(?:\n|$))+)/gi;

	interface MatchRange {
		start: number;
		end: number;
		segment: Segment;
	}

	const ranges: MatchRange[] = [];

	let m: RegExpExecArray | null;
	while ((m = cardPattern.exec(markdown)) !== null) {
		const rawImgAlt = m[1] || m[4] || "";
		const rawImgUrl = m[2] || m[5] || "";
		const headerTitle = m[3] || "";
		const isTreatment = /treatment|tindakan|prosedur|protokol/i.test(headerTitle);
		const bulletsText = m[6] || "";

		const items = parseBulletLines(bulletsText);
		const cleanImgUrl = isValidImageUrl(rawImgUrl) ? resolveImageUrl(rawImgUrl) : undefined;

		ranges.push({
			start: m.index,
			end: cardPattern.lastIndex,
			segment: {
				type: isTreatment ? "treatment-card" : "product-card",
				content: m[0],
				data: {
					imageUrl: cleanImgUrl,
					imageAlt: rawImgAlt,
					items,
				},
			},
		});
	}

	while ((m = regimenPattern.exec(markdown)) !== null) {
		const bulletsText = m[1] || "";
		const items = parseBulletLines(bulletsText);
		ranges.push({
			start: m.index,
			end: regimenPattern.lastIndex,
			segment: {
				type: "regimen-card",
				content: m[0],
				data: { items },
			},
		});
	}

	while ((m = dosDontsPattern.exec(markdown)) !== null) {
		const bulletsText = m[1] || "";
		const items = parseBulletLines(bulletsText);
		ranges.push({
			start: m.index,
			end: dosDontsPattern.lastIndex,
			segment: {
				type: "dos-donts-card",
				content: m[0],
				data: { items },
			},
		});
	}

	// Sort ranges by start index and filter out overlapping ranges
	ranges.sort((a, b) => a.start - b.start);

	const segments: Segment[] = [];
	let lastIndex = 0;

	for (const range of ranges) {
		if (range.start < lastIndex) continue; // Skip overlaps

		if (range.start > lastIndex) {
			const beforeText = markdown.slice(lastIndex, range.start);
			if (beforeText.trim()) {
				segments.push({ type: "markdown", content: beforeText });
			}
		}

		segments.push(range.segment);
		lastIndex = range.end;
	}

	if (lastIndex < markdown.length) {
		const remainingText = markdown.slice(lastIndex);
		if (remainingText.trim()) {
			segments.push({ type: "markdown", content: remainingText });
		}
	}

	return segments.length > 0 ? segments : [{ type: "markdown", content: markdown }];
}

function ProductCard({ data }: { data: CardData }) {
	const { imageUrl, imageAlt, items } = data;

	let productName = "";
	let brand = "";
	let variant = "";
	let productType = "";
	let skinTypes = "";
	let netContent = "";
	let price = "";
	let sku = "";
	let bpom = "";
	let texture = "";
	let usage = "";
	let ageGroup = "";
	let sideEffects = "";
	const otherItems: KeyValueItem[] = [];

	for (const item of items) {
		const k = item.key.toLowerCase();
		if (k.includes("product name") || k.includes("nama produk")) {
			productName = item.value;
		} else if (k.includes("brand") || k.includes("merek")) {
			brand = item.value;
		} else if (k.includes("variant") || k.includes("varian")) {
			variant = item.value;
		} else if (
			k.includes("product type") ||
			k.includes("tipe produk") ||
			k.includes("jenis produk")
		) {
			productType = item.value;
		} else if (
			k.includes("skin type") ||
			k.includes("jenis kulit") ||
			k.includes("target kondisi")
		) {
			skinTypes = item.value;
		} else if (
			k.includes("net content") ||
			k.includes("berat bersih") ||
			k.includes("volume") ||
			k.includes("isi bersih")
		) {
			netContent = item.value;
		} else if (k.includes("harga") || k.includes("price")) {
			price = item.value;
		} else if (k.includes("sku") || k.includes("kode sku")) {
			sku = item.value;
		} else if (k.includes("bpom") || k.includes("registrasi")) {
			bpom = item.value;
		} else if (k.includes("tekstur") || k.includes("texture") || k.includes("sediaan")) {
			texture = item.value;
		} else if (k.includes("aturan pakai") || k.includes("cara pakai") || k.includes("dosis")) {
			usage = item.value;
		} else if (k.includes("target usia") || k.includes("usia") || k.includes("age")) {
			ageGroup = item.value;
		} else if (k.includes("efek samping") || k.includes("side effect")) {
			sideEffects = item.value;
		} else {
			otherItems.push(item);
		}
	}

	return (
		<div className="not-prose my-2 rounded-lg border border-zinc-200/80 bg-white p-3 flex flex-col sm:flex-row gap-3 items-start shadow-none">
			{imageUrl && (
				<div className="size-24 sm:size-28 shrink-0 bg-zinc-50 rounded-md border border-zinc-200/80 p-1 flex items-center justify-center overflow-hidden relative group cursor-pointer">
					{/* eslint-disable-next-line @next/next/no-img-element */}
					<img
						src={imageUrl}
						alt={imageAlt || productName || "Product"}
						className="size-full object-contain transition-transform duration-150 group-hover:scale-105"
						loading="lazy"
						onClick={() => window.open(imageUrl, "_blank", "noopener,noreferrer")}
					/>
					<button
						type="button"
						onClick={() => window.open(imageUrl, "_blank", "noopener,noreferrer")}
						className="absolute bottom-1 right-1 p-1 rounded bg-white/90 text-zinc-600 border border-zinc-200/80 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
						title="Open image"
					>
						<RiZoomInLine className="size-3" />
					</button>
				</div>
			)}

			<div className="flex-1 min-w-0 flex flex-col justify-between self-stretch">
				<div className="flex flex-col gap-1 text-[13px] text-zinc-900 leading-normal">
					{/* 1. Product Title */}
					{productName && (
						<h4 className="text-[14px] font-semibold text-zinc-950 leading-snug tracking-tight">
							{productName}
						</h4>
					)}

					{/* 2. Brand / Product Type / Variant Badges */}
					{(brand || productType || variant) && (
						<div className="flex items-center gap-1.5 flex-wrap my-0.5">
							{brand && (
								<span className="text-[11px] font-medium text-zinc-800 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200">
									{brand}
								</span>
							)}
							{productType && (
								<span className="text-[11px] font-normal text-zinc-700 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200/80">
									{productType}
								</span>
							)}
							{variant && (
								<span className="text-[11px] font-normal text-zinc-700 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200/80">
									{variant}
								</span>
							)}
						</div>
					)}

					{/* 3. Net Content */}
					{netContent && (
						<div>
							<span className="text-zinc-600 font-normal">Net Content:</span>{" "}
							<span className="text-zinc-900 font-normal">{netContent}</span>
						</div>
					)}

					{/* 4. Skin Types */}
					{skinTypes && (
						<div>
							<span className="text-zinc-600 font-normal">Skin Types:</span>{" "}
							<span className="text-zinc-900 font-normal">{skinTypes}</span>
						</div>
					)}

					{/* 5. Tekstur / Sediaan */}
					{texture && (
						<div>
							<span className="text-zinc-600 font-normal">Tekstur:</span>{" "}
							<span className="text-zinc-900 font-normal">{texture}</span>
						</div>
					)}

					{/* 6. Aturan Pakai */}
					{usage && (
						<div>
							<span className="text-zinc-600 font-normal">Aturan Pakai:</span>{" "}
							<span className="text-zinc-900 font-normal">{usage}</span>
						</div>
					)}

					{/* 7. Target Usia */}
					{ageGroup && (
						<div>
							<span className="text-zinc-600 font-normal">Target Usia:</span>{" "}
							<span className="text-zinc-900 font-normal">{ageGroup}</span>
						</div>
					)}

					{/* 8. No BPOM */}
					{bpom && (
						<div>
							<span className="text-zinc-600 font-normal">No BPOM:</span>{" "}
							<span className="font-mono text-zinc-800 text-xs bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200">
								{bpom}
							</span>
						</div>
					)}

					{/* 9. Efek Samping */}
					{sideEffects && (
						<div>
							<span className="text-zinc-600 font-normal">Efek Samping:</span>{" "}
							<span className="text-zinc-900 font-normal">{sideEffects}</span>
						</div>
					)}

					{/* 10. Other custom items */}
					{otherItems.map((item, idx) => (
						<div key={idx}>
							<span className="text-zinc-600 font-normal">{item.key}:</span>{" "}
							<span className="text-zinc-900 font-normal">{item.value}</span>
						</div>
					))}
				</div>

				{/* Price & SKU footer */}
				{(price || sku) && (
					<div className="mt-1.5 pt-0.5 flex items-center justify-between flex-wrap gap-2">
						{price && <span className="text-[13.5px] font-semibold text-zinc-950">{price}</span>}
						{sku && <span className="text-xs font-mono font-normal text-zinc-600">SKU: {sku}</span>}
					</div>
				)}
			</div>
		</div>
	);
}

function TreatmentCard({ data }: { data: CardData }) {
	const { imageUrl, imageAlt, items } = data;

	let treatmentName = "";
	let category = "";
	let duration = "";
	let downtime = "";
	let anesthesia = "";
	let indications = "";
	let price = "";
	let interval = "";
	let sideEffects = "";
	const otherItems: KeyValueItem[] = [];

	for (const item of items) {
		const k = item.key.toLowerCase();
		if (
			k.includes("treatment name") ||
			k.includes("nama tindakan") ||
			k.includes("nama treatment")
		) {
			treatmentName = item.value;
		} else if (k.includes("category") || k.includes("kategori") || k.includes("tipe")) {
			category = item.value;
		} else if (k.includes("duration") || k.includes("durasi") || k.includes("waktu")) {
			duration = item.value;
		} else if (k.includes("downtime") || k.includes("pemulihan")) {
			downtime = item.value;
		} else if (k.includes("anestesi") || k.includes("anesthesia")) {
			anesthesia = item.value;
		} else if (k.includes("indikasi") || k.includes("target") || k.includes("skin type")) {
			indications = item.value;
		} else if (k.includes("harga") || k.includes("price") || k.includes("biaya")) {
			price = item.value;
		} else if (k.includes("interval") || k.includes("sesi") || k.includes("frekuensi")) {
			interval = item.value;
		} else if (k.includes("efek samping") || k.includes("side effect")) {
			sideEffects = item.value;
		} else {
			otherItems.push(item);
		}
	}

	return (
		<div className="not-prose my-2 rounded-lg border border-zinc-200/80 bg-white p-3 flex flex-col sm:flex-row gap-3 items-start shadow-none">
			{imageUrl ? (
				<div className="size-24 sm:size-28 shrink-0 bg-zinc-50 rounded-md border border-zinc-200/80 p-1 flex items-center justify-center overflow-hidden relative group cursor-pointer">
					{/* eslint-disable-next-line @next/next/no-img-element */}
					<img
						src={imageUrl}
						alt={imageAlt || treatmentName || "Treatment"}
						className="size-full object-contain transition-transform duration-150 group-hover:scale-105"
						loading="lazy"
						onClick={() => window.open(imageUrl, "_blank", "noopener,noreferrer")}
					/>
					<button
						type="button"
						onClick={() => window.open(imageUrl, "_blank", "noopener,noreferrer")}
						className="absolute bottom-1 right-1 p-1 rounded bg-white/90 text-zinc-600 border border-zinc-200/80 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
						title="Open image"
					>
						<RiZoomInLine className="size-3" />
					</button>
				</div>
			) : (
				<div className="size-12 sm:size-14 shrink-0 bg-zinc-100 rounded-lg border border-zinc-200 flex items-center justify-center text-zinc-600">
					<RiStethoscopeLine className="size-6" />
				</div>
			)}

			<div className="flex-1 min-w-0 flex flex-col justify-between self-stretch">
				<div className="flex flex-col gap-1 text-[13px] text-zinc-900 leading-normal">
					{/* Treatment Title */}
					{treatmentName && (
						<h4 className="text-[14px] font-semibold text-zinc-950 leading-snug tracking-tight">
							{treatmentName}
						</h4>
					)}

					{/* Category Badge */}
					{category && (
						<div className="flex items-center gap-1.5 flex-wrap my-0.5">
							<span className="text-[11px] font-medium text-zinc-800 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200">
								{category}
							</span>
						</div>
					)}

					{/* 3. Single-column Specifications */}
					{duration && (
						<div>
							<span className="text-zinc-600 font-normal">Durasi:</span>{" "}
							<span className="text-zinc-900 font-normal">{duration}</span>
						</div>
					)}

					{downtime && (
						<div>
							<span className="text-zinc-600 font-normal">Downtime:</span>{" "}
							<span className="text-zinc-900 font-normal">{downtime}</span>
						</div>
					)}

					{anesthesia && (
						<div>
							<span className="text-zinc-600 font-normal">Anestesi:</span>{" "}
							<span className="text-zinc-900 font-normal">{anesthesia}</span>
						</div>
					)}

					{/* Target Indikasi */}
					{indications && (
						<div>
							<span className="text-zinc-600 font-normal">Indikasi:</span>{" "}
							<span className="text-zinc-900 font-normal">{indications}</span>
						</div>
					)}

					{/* Sesi Interval */}
					{interval && (
						<div>
							<span className="text-zinc-600 font-normal">Sesi Disarankan:</span>{" "}
							<span className="text-zinc-900 font-normal">{interval}</span>
						</div>
					)}

					{/* Efek Samping */}
					{sideEffects && (
						<div>
							<span className="text-zinc-600 font-normal">Efek Samping:</span>{" "}
							<span className="text-zinc-900 font-normal">{sideEffects}</span>
						</div>
					)}

					{/* Other custom items */}
					{otherItems.map((item, idx) => (
						<div key={idx}>
							<span className="text-zinc-600 font-normal">{item.key}:</span>{" "}
							<span className="text-zinc-900 font-normal">{item.value}</span>
						</div>
					))}
				</div>

				{/* Price Footer */}
				{price && (
					<div className="mt-1.5 pt-0.5 flex items-center justify-between flex-wrap gap-2">
						<span className="text-[13.5px] font-semibold text-zinc-950">{price}</span>
						<span className="text-xs text-zinc-600 font-normal">Estimasi per sesi</span>
					</div>
				)}
			</div>
		</div>
	);
}

function RegimenCard({ data }: { data: CardData }) {
	const { items } = data;

	return (
		<div className="not-prose my-2 rounded-lg border border-zinc-200/80 bg-zinc-50/50 p-2.5 flex flex-col gap-2">
			<div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
				{items.map((item, idx) => {
					const isNight = /malam|night|evening/i.test(item.key);
					return (
						<div
							key={idx}
							className={`p-2 rounded-md border text-xs ${
								isNight ? "border-zinc-200 bg-white" : "border-zinc-200 bg-white"
							}`}
						>
							<div className="flex items-center gap-1.5 mb-1">
								<span className="text-[11px] font-medium text-zinc-800 bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200">
									{item.key}
								</span>
							</div>
							<p className="text-[12.5px] text-zinc-900 leading-normal m-0">{item.value}</p>
						</div>
					);
				})}
			</div>
		</div>
	);
}

function DosAndDontsCard({ data }: { data: CardData }) {
	const { items } = data;

	const dosItems = items.filter((item) => /do|anjuran|boleh|disarankan/i.test(item.key));
	const dontsItems = items.filter((item) => /don't|larangan|dilarang|tidak boleh/i.test(item.key));

	return (
		<div className="not-prose my-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
			{dosItems.length > 0 && (
				<div className="p-2.5 rounded-md border-l-2 border-emerald-600 bg-emerald-50/30 text-xs">
					<span className="block text-[11.5px] font-semibold text-emerald-950 mb-1">
						Anjuran (Do&apos;s)
					</span>
					<div className="space-y-1">
						{dosItems.map((item, idx) => (
							<div key={idx} className="text-zinc-900 leading-normal">
								{item.value}
							</div>
						))}
					</div>
				</div>
			)}
			{dontsItems.length > 0 && (
				<div className="p-2.5 rounded-md border-l-2 border-red-600 bg-red-50/30 text-xs">
					<span className="block text-[11.5px] font-semibold text-red-950 mb-1">
						Larangan (Don&apos;ts)
					</span>
					<div className="space-y-1">
						{dontsItems.map((item, idx) => (
							<div key={idx} className="text-zinc-900 leading-normal">
								{item.value}
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
}

function extractNodeText(node: React.ReactNode): string {
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

export const defaultMarkdownComponents: Components = {
	img: ({ src, alt, ...props }) => {
		const strSrc = typeof src === "string" ? src.trim() : "";
		if (!isValidImageUrl(strSrc)) {
			return null;
		}

		const resolvedSrc = resolveImageUrl(strSrc);

		return (
			<span className="my-1.5 inline-block max-w-full rounded-lg border border-zinc-200 bg-zinc-50/50 overflow-hidden align-top">
				{/* eslint-disable-next-line @next/next/no-img-element */}
				<img
					src={resolvedSrc}
					alt={typeof alt === "string" ? alt : "Document Image"}
					className="max-h-64 w-auto max-w-full object-contain cursor-pointer transition hover:opacity-90 block"
					loading="lazy"
					onClick={() => {
						if (resolvedSrc) {
							window.open(resolvedSrc, "_blank", "noopener,noreferrer");
						}
					}}
					onError={(e) => {
						const parent = e.currentTarget.parentElement;
						if (parent) {
							parent.style.display = "none";
						}
					}}
					{...props}
				/>
				{alt && typeof alt === "string" && (
					<span className="block px-2 py-0.5 text-[11px] text-zinc-600 font-normal bg-white truncate max-w-full">
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
				className={`my-1 py-1 px-2.5 rounded-r-md ${borderClass} text-xs leading-normal shadow-none [&>p]:m-0`}
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
				<details className="my-1.5 p-2 rounded-md border border-zinc-200 bg-white group [&_summary::-webkit-details-marker]:hidden">
					<summary className="cursor-pointer text-[13px] font-medium text-zinc-900 flex items-center justify-between gap-2 list-none select-none">
						<span className="flex items-center gap-1.5">
							<span className="text-[11px] font-semibold text-zinc-700 bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200">
								Q
							</span>
							<span>{question}</span>
						</span>
						<span className="text-zinc-400 text-xs font-mono transition-transform group-open:rotate-180">
							▾
						</span>
					</summary>
					<div className="pt-2 pl-6 text-[12.5px] text-zinc-700 leading-normal border-t border-zinc-100 mt-2">
						{answer}
					</div>
				</details>
			);
		}
		return <p className="my-1 text-[13px] text-zinc-900 leading-normal font-normal">{children}</p>;
	},
	ol: ({ children }) => (
		<ol className="list-decimal pl-4.5 my-1 space-y-0.5 text-[13px] text-zinc-900 leading-normal font-normal marker:text-zinc-600">
			{children}
		</ol>
	),
	ul: ({ children }) => (
		<ul className="list-disc pl-4.5 my-1 space-y-0.5 text-[13px] text-zinc-900 leading-normal font-normal marker:text-zinc-500">
			{children}
		</ul>
	),
	li: ({ children }) => (
		<li className="text-[13px] leading-normal text-zinc-900 font-normal">{children}</li>
	),
	h1: ({ children }) => (
		<h1 className="text-[15.5px] font-semibold text-zinc-950 first:mt-1 mt-4 mb-2 tracking-tight">
			{children}
		</h1>
	),
	h2: ({ children }) => (
		<h2 className="text-[14.5px] font-semibold text-zinc-950 first:mt-1 mt-6 mb-1.5 flex items-center gap-2 tracking-tight">
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
				className={`text-[13px] font-semibold mt-2.5 mb-0.5 flex items-center gap-1.5 ${
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
	strong: ({ children }) => <strong className="font-medium text-zinc-950">{children}</strong>,
	hr: () => <div className="my-1.5" />,
	table: ({ children }) => (
		<div className="my-1.5 overflow-x-auto rounded-md border border-zinc-200 bg-white">
			<table className="w-full text-left text-xs border-collapse divide-y divide-zinc-200">
				{children}
			</table>
		</div>
	),
	thead: ({ children }) => (
		<thead className="bg-zinc-50 text-zinc-900 font-semibold">{children}</thead>
	),
	tbody: ({ children }) => <tbody className="divide-y divide-zinc-100 bg-white">{children}</tbody>,
	tr: ({ children }) => <tr className="hover:bg-zinc-50/60 transition-colors">{children}</tr>,
	th: ({ children }) => <th className="px-2.5 py-1.5 font-semibold text-zinc-800">{children}</th>,
	td: ({ children }) => <td className="px-2.5 py-1.5 text-zinc-800 font-normal">{children}</td>,
};

export function MarkdownContent({
	content,
	components,
}: {
	content: string;
	components?: Components;
}) {
	const mergedComponents = { ...defaultMarkdownComponents, ...components };
	const segments = parseMarkdownSegments(content);

	if (segments.length === 1 && segments[0].type === "markdown") {
		return (
			<ReactMarkdown remarkPlugins={[remarkGfm]} components={mergedComponents}>
				{content}
			</ReactMarkdown>
		);
	}

	return (
		<div className="flex flex-col gap-1">
			{segments.map((seg, idx) => {
				if (seg.type === "product-card" && seg.data) {
					return <ProductCard key={idx} data={seg.data} />;
				}
				if (seg.type === "treatment-card" && seg.data) {
					return <TreatmentCard key={idx} data={seg.data} />;
				}
				if (seg.type === "regimen-card" && seg.data) {
					return <RegimenCard key={idx} data={seg.data} />;
				}
				if (seg.type === "dos-donts-card" && seg.data) {
					return <DosAndDontsCard key={idx} data={seg.data} />;
				}
				return (
					<ReactMarkdown key={idx} remarkPlugins={[remarkGfm]} components={mergedComponents}>
						{seg.content}
					</ReactMarkdown>
				);
			})}
		</div>
	);
}
