import React, { useState } from "react";
import { RiImageLine } from "@remixicon/react";
import type { BeforeAfterData } from "../types";
import { ImagePreviewDialog } from "@/components/shared/image-preview-dialog";

export function BeforeAfterCard({ data }: { data: BeforeAfterData }) {
	const { beforeImage, afterImage } = data;
	const [previewState, setPreviewState] = useState<{
		isOpen: boolean;
		url: string;
		alt: string;
	}>({
		isOpen: false,
		url: "",
		alt: "",
	});

	return (
		<>
			<div className="not-prose my-2.5 flex flex-col sm:flex-row gap-2.5 items-stretch w-full">
				{/* Left / Before Image */}
				<span className="flex-1 min-w-35 max-w-full rounded-lg border border-zinc-200/80 bg-zinc-50/50 overflow-hidden align-top inline-flex flex-col">
					<span className="h-44 sm:h-48 w-full p-1.5 flex items-center justify-center overflow-hidden relative group">
						{/* eslint-disable-next-line @next/next/no-img-element */}
						<img
							src={beforeImage.url}
							alt={beforeImage.alt || "Sebelum Perawatan"}
							className="size-full object-contain cursor-pointer transition hover:opacity-90 block"
							loading="lazy"
							onClick={() => {
								if (beforeImage.url) {
									setPreviewState({
										isOpen: true,
										url: beforeImage.url,
										alt: beforeImage.alt || "Sebelum Perawatan",
									});
								}
							}}
							onError={(e) => {
								e.currentTarget.style.display = "none";
								const fallback = e.currentTarget.nextElementSibling as HTMLElement;
								if (fallback) fallback.style.display = "flex";
							}}
						/>
						<span
							style={{ display: "none" }}
							className="size-full bg-zinc-100 items-center justify-center text-zinc-400 text-xs flex-col p-2 text-center select-none"
						>
							<RiImageLine className="size-6 text-zinc-400 mb-1" />
							<span className="text-xs text-zinc-400 font-medium">Gambar Tidak Tersedia</span>
						</span>
					</span>
					{beforeImage.alt && (
						<span className="block px-2.5 py-1 text-xs text-zinc-600 font-medium bg-white border-t border-zinc-100 truncate w-full text-center">
							{beforeImage.alt}
						</span>
					)}
				</span>

				{/* Right / After Image */}
				<span className="flex-1 min-w-35 max-w-full rounded-lg border border-zinc-200/80 bg-zinc-50/50 overflow-hidden align-top inline-flex flex-col">
					<span className="h-44 sm:h-48 w-full p-1.5 flex items-center justify-center overflow-hidden relative group">
						{/* eslint-disable-next-line @next/next/no-img-element */}
						<img
							src={afterImage.url}
							alt={afterImage.alt || "Sesudah Perawatan"}
							className="size-full object-contain cursor-pointer transition hover:opacity-90 block"
							loading="lazy"
							onClick={() => {
								if (afterImage.url) {
									setPreviewState({
										isOpen: true,
										url: afterImage.url,
										alt: afterImage.alt || "Sesudah Perawatan",
									});
								}
							}}
							onError={(e) => {
								e.currentTarget.style.display = "none";
								const fallback = e.currentTarget.nextElementSibling as HTMLElement;
								if (fallback) fallback.style.display = "flex";
							}}
						/>
						<span
							style={{ display: "none" }}
							className="size-full bg-zinc-100 items-center justify-center text-zinc-400 text-xs flex-col p-2 text-center select-none"
						>
							<RiImageLine className="size-6 text-zinc-400 mb-1" />
							<span className="text-xs text-zinc-400 font-medium">Gambar Tidak Tersedia</span>
						</span>
					</span>
					{afterImage.alt && (
						<span className="block px-2.5 py-1 text-xs text-zinc-600 font-medium bg-white border-t border-zinc-100 truncate w-full text-center">
							{afterImage.alt}
						</span>
					)}
				</span>
			</div>

			<ImagePreviewDialog
				src={previewState.url}
				alt={previewState.alt}
				isOpen={previewState.isOpen}
				onOpenChange={(open) => setPreviewState((prev) => ({ ...prev, isOpen: open }))}
			/>
		</>
	);
}
