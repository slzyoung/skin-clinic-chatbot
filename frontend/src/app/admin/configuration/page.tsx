"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { BranchTokenTable } from "./components/branch-token-table";
import { GlobalTokenConfig } from "./components/global-token-config";
import { useConfigs, useUpdateConfig } from "./hooks/use-config";

export default function ConfigPage() {
	const { data: configs } = useConfigs();
	const updateConfig = useUpdateConfig();

	const initialOpenAiKey = configs?.find((c) => c.key === "OPENAI_API_KEY")?.value || "";
	const [editedKey, setEditedKey] = useState<string | null>(null);

	const openAiKey = editedKey !== null ? editedKey : initialOpenAiKey;

	const handleSave = () => {
		updateConfig.mutate({
			key: "OPENAI_API_KEY",
			data: { value: openAiKey },
		});
	};

	return (
		<div className="flex flex-col flex-1 min-h-full bg-white p-6">
			<div className="flex flex-col gap-6 w-full">
				{/* Header */}
				<div className="flex flex-col gap-1">
					<h1 className="text-xl font-semibold text-black-500">Configuration</h1>
					<p className="text-sm text-black-300">Here is the overview data of the configuration</p>
				</div>

				{/* Content */}
				<div className="flex flex-col gap-6">
					<div className="border border-gray-100 rounded-md p-6 flex flex-col gap-4 max-w-2xl">
						<h2 className="text-lg font-medium text-gray-900">AI Model Configuration</h2>
						<div className="flex flex-col gap-1.5">
							<Label htmlFor="openai_key" className="text-sm font-medium text-gray-900">
								OpenAI API Key
							</Label>
							<Input
								id="openai_key"
								type="password"
								placeholder="sk-..."
								className="border-gray-200 bg-white"
								value={openAiKey}
								onChange={(e) => setEditedKey(e.target.value)}
							/>
							<p className="text-xs text-gray-500">
								The API key used for generating AI chatbot responses and processing documents.
							</p>
						</div>
						<div className="flex justify-end mt-2">
							<Button
								className="bg-blue-600 hover:bg-blue-700"
								onClick={handleSave}
								disabled={updateConfig.isPending}
							>
								{updateConfig.isPending ? "Saving..." : "Save Configuration"}
							</Button>
						</div>
					</div>

					<GlobalTokenConfig />
					<BranchTokenTable />
				</div>
			</div>
		</div>
	);
}
