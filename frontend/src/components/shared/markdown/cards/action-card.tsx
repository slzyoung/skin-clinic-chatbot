import React from "react";
import { RiDeleteBin7Line, RiEdit2Line } from "@remixicon/react";
import type { ActionConfirmationData } from "../types";

export function ActionConfirmationCard({ data }: { data: ActionConfirmationData }) {
	const {
		actionType,
		knowledgeId,
		fieldName,
		newValue,
		summary,
		confirmationPrompt,
	} = data;
	const isDelete = actionType === "delete_preview";

	return (
		<div className="not-prose my-2.5 rounded-lg border border-zinc-200/80 bg-white p-3.5 flex flex-col gap-2.5 shadow-none">
			{/* Header */}
			<div className="flex items-center justify-between gap-2 border-b border-zinc-100 pb-2">
				<div className="flex items-center gap-2 min-w-0">
					<div
						className={`size-6 rounded-md flex items-center justify-center shrink-0 ${
							isDelete ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-600"
						}`}
					>
						{isDelete ? (
							<RiDeleteBin7Line className="size-3.5" />
						) : (
							<RiEdit2Line className="size-3.5" />
						)}
					</div>
					<h4 className="text-sm font-semibold text-zinc-950 tracking-tight">
						{isDelete ? "Konfirmasi Penghapusan Dokumen" : "Pratinjau Perubahan Data"}
					</h4>
				</div>
				<span
					className={`text-xs font-medium px-2 py-0.5 rounded border ${
						isDelete
							? "bg-red-50 text-red-700 border-red-200/80"
							: "bg-blue-50 text-blue-700 border-blue-200/80"
					}`}
				>
					{isDelete ? "Penghapusan" : "Pembaruan"}
				</span>
			</div>

			{/* Details Box */}
			<div className="rounded-md border border-zinc-100 bg-zinc-50/60 p-2.5 text-xs sm:text-sm text-zinc-800 space-y-1.5">
				{knowledgeId && (
					<div className="flex items-center gap-2 flex-wrap">
						<span className="text-zinc-500 font-medium">Knowledge ID:</span>
						<span className="font-mono text-xs bg-white px-1.5 py-0.5 rounded border border-zinc-200 text-zinc-800">
							{knowledgeId}
						</span>
					</div>
				)}
				{fieldName && (
					<div className="flex items-center gap-2 flex-wrap">
						<span className="text-zinc-500 font-medium">Bagian / Field:</span>
						<span className="font-semibold text-zinc-950">{fieldName}</span>
					</div>
				)}
				{newValue && (
					<div className="flex items-center gap-2 flex-wrap">
						<span className="text-zinc-500 font-medium">Nilai Baru:</span>
						<span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200/70">
							{newValue}
						</span>
					</div>
				)}
				{summary && <p className="m-0 text-zinc-700 leading-normal pt-1">{summary}</p>}
			</div>

			{confirmationPrompt && (
				<p className="text-xs text-zinc-500 italic m-0">
					{confirmationPrompt}
				</p>
			)}
		</div>
	);
}
