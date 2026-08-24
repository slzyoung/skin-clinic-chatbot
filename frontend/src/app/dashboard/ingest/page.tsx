"use client";

import { PromptInput } from "@/components/shared/prompt-input";
import {
	RiFileTextLine,
	RiMedicineBottleLine,
	RiRobot2Line,
	RiSyringeLine,
	RiAlertLine,
} from "@remixicon/react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useMemo, Suspense } from "react";
import { useUploadKnowledge, useIngestionQuota } from "../knowledge/hooks/use-knowledge";
import { useProjects } from "../knowledge/hooks/use-projects";

function IngestContent() {
	const router = useRouter();
	const searchParams = useSearchParams();
	const projectId = searchParams.get("projectId") || searchParams.get("project_id");

	const { data: projects = [] } = useProjects();
	const uploadMutation = useUploadKnowledge();
	const { data: quota } = useIngestionQuota();

	const [selectedProjectId, setSelectedProjectId] = useState<string>(projectId || "none");
	const [errorMsg, setErrorMsg] = useState<string | null>(null);
	const [promptValue, setPromptValue] = useState("");

	const selectedProjectName = useMemo(() => {
		if (!selectedProjectId || selectedProjectId === "none") {
			return "No Project";
		}
		const found = projects.find((p) => p.id === selectedProjectId);
		return found ? found.name : "Select Project";
	}, [selectedProjectId, projects]);

	const handleSend = (value: string, _category: string | undefined, files: File[]) => {
		if (files.length === 0) {
			setErrorMsg("Please attach at least one file to ingest.");
			return false;
		}

		setErrorMsg(null);

		const formData = new FormData();
		if (value) {
			formData.append("prompt", value);
		}

		const targetProject = selectedProjectId !== "none" ? selectedProjectId : null;
		if (targetProject) {
			formData.append("project_id", targetProject);
		}

		files.forEach((file) => {
			formData.append("file", file);
		});

		uploadMutation.mutate(formData, {
			onSuccess: (data: { batch_id?: string; upload_batch_id?: string; documents?: { knowledge_id: string }[] }) => {
				const batchId = data.batch_id || data.upload_batch_id;
				if (batchId) {
					router.push(`/dashboard/knowledge/batch/${batchId}`);
				} else if (data.documents && data.documents.length > 0) {
					router.push(`/dashboard/knowledge/${data.documents[0].knowledge_id}`);
				} else if (targetProject) {
					router.push(`/dashboard/knowledge/project/${targetProject}`);
				} else {
					router.push("/dashboard/knowledge");
				}
			},
		});
	};

	return (
		<div className="flex flex-col max-w-2xl mx-auto min-h-full w-full pt-10 pb-10 px-4">
			{/* Header */}
			<div className="flex flex-col items-center text-center space-y-2 mb-8">
				<div className="flex aspect-square size-12 items-center justify-center rounded-md bg-blue-50 text-blue-500">
					<RiRobot2Line className="size-6" />
				</div>
				<div className="space-y-1">
					<h1 className="text-lg font-semibold tracking-tight text-zinc-950">
						Expand our clinical knowledge today
					</h1>
					<p className="text-[13px] text-zinc-500 max-w-95 leading-relaxed">
						Ingesting documents to train the ai erha knowledge with product, treatment, and
						promotional brochure
					</p>
				</div>
			</div>

			{/* Ingestion Quota Warning Banner (Only displayed when approaching or reaching threshold) */}
			{quota && (quota.exceeded || quota.warning) && (
				<div className="mb-5 w-full">
					{quota.exceeded ? (
						<div className="flex items-start gap-3 p-3.5 rounded-lg border border-amber-300 bg-white text-xs">
							<RiAlertLine className="size-4 text-amber-600 shrink-0 mt-0.5" />
							<div className="flex flex-col gap-0.5">
								<span className="font-semibold text-zinc-900">Monthly Ingestion Threshold Reached ({quota.percentage}%)</span>
								<span className="text-zinc-500">
									You have used {quota.tokens_used.toLocaleString()} of {quota.token_limit.toLocaleString()} tokens this month. Ingestion will proceed normally, but you can adjust the threshold anytime in Configuration.
								</span>
							</div>
						</div>
					) : (
						<div className="flex items-start gap-3 p-3.5 rounded-lg border border-amber-300 bg-white text-xs">
							<RiAlertLine className="size-4 text-amber-600 shrink-0 mt-0.5" />
							<div className="flex flex-col gap-0.5">
								<span className="font-semibold text-zinc-900">Monthly Ingestion Quota Near Limit</span>
								<span className="text-zinc-500">
									{quota.tokens_used.toLocaleString()} of {quota.token_limit.toLocaleString()} tokens used ({quota.percentage}%). Approaching monthly capacity.
								</span>
							</div>
						</div>
					)}
				</div>
			)}

			{/* Shortcuts */}
			<div className="grid grid-cols-2 gap-3 w-full mb-4 shrink-0">
				<button
					type="button"
					onClick={() => setPromptValue("Can you suggest a product for this condition...")}
					className="flex flex-col items-start p-3 text-left rounded-xl border border-zinc-200/70 bg-white hover:border-zinc-300 hover:bg-zinc-50/60 transition-all cursor-pointer shadow-none"
				>
					<RiMedicineBottleLine className="size-4 text-zinc-950 mb-1.5" />
					<h3 className="font-semibold text-xs text-zinc-950 mb-0.5">Product Knowledge</h3>
					<p className="text-[11px] leading-tight text-zinc-500">
						Can you suggest a product for this condition...
					</p>
				</button>
				<button
					type="button"
					onClick={() => setPromptValue("Could you recommend a treatment for this condition...")}
					className="flex flex-col items-start p-3 text-left rounded-xl border border-zinc-200/70 bg-white hover:border-zinc-300 hover:bg-zinc-50/60 transition-all cursor-pointer shadow-none"
				>
					<RiSyringeLine className="size-4 text-zinc-950 mb-1.5" />
					<h3 className="font-semibold text-xs text-zinc-950 mb-0.5">Treatment Recomendation</h3>
					<p className="text-[11px] leading-tight text-zinc-500">
						Could you recommend a treatment for this condition...
					</p>
				</button>
			</div>

			{/* Prompt Input */}
			<div className="shrink-0 mt-4 flex flex-col items-center relative">
				<div className="w-full">
					<PromptInput
						key={promptValue}
						defaultValue={promptValue}
						minRows={3}
						onSend={handleSend}
						showAttachText={true}
						attachText="Add files"
						disabled={uploadMutation.isPending}
					/>
				</div>

				{errorMsg && (
					<div className="w-full mt-2 flex items-center text-[13px] font-medium text-amber-600 bg-amber-50 border border-amber-200/80 rounded-lg p-2.5">
						<RiAlertLine className="size-4 mr-1.5 shrink-0" />
						{errorMsg}
					</div>
				)}

				{/* Project Attachment Selector below chat prompt on right */}
				<div className="w-full flex items-center justify-end mt-3 px-0.5">
					<div className="flex items-center gap-2 max-w-full">
						<span className="text-xs text-zinc-500 font-medium shrink-0">Attach to Project:</span>
						<Select
							value={selectedProjectId}
							onValueChange={(val) => setSelectedProjectId(val ?? "none")}
							disabled={uploadMutation.isPending}
						>
							<SelectTrigger className="h-8 text-xs border-zinc-200/80 bg-white text-zinc-700 rounded-lg px-2.5 min-w-36 max-w-56 sm:max-w-72 shadow-none hover:border-zinc-300 transition-colors">
								<SelectValue placeholder="Select Project" className="truncate">
									{selectedProjectName}
								</SelectValue>
							</SelectTrigger>
							<SelectContent align="end" alignItemWithTrigger={false} sideOffset={4} className="bg-white max-w-xs">
								<SelectItem value="none">
									<span className="truncate">No Project</span>
								</SelectItem>
								{projects.map((p) => (
									<SelectItem key={p.id} value={p.id}>
										<span className="truncate" title={p.name}>{p.name}</span>
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
				</div>

				{uploadMutation.isPending && (
					<div className="absolute inset-0 bg-white/50 flex items-center justify-center rounded-xl z-10 backdrop-blur-sm">
						<span className="text-sm font-medium text-blue-600">Uploading documents...</span>
					</div>
				)}

				<div className="mt-4 px-3.5 py-1.5 w-fit mx-auto border border-zinc-200/60 rounded-full flex items-center justify-center text-[11px] text-zinc-400 bg-zinc-50/50">
					<RiFileTextLine className="size-3 mr-1.5 text-zinc-400" />
					File format including PDF, docx, excel, image
				</div>
			</div>
		</div>
	);
}

export default function IngestPage() {
	return (
		<Suspense fallback={<div className="p-8 text-center text-sm text-gray-500">Loading ingestion...</div>}>
			<IngestContent />
		</Suspense>
	);
}
