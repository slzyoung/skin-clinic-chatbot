"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { RiCheckLine, RiEdit2Line, RiLoader4Line, RiEyeLine, RiEyeOffLine } from "@remixicon/react";
import * as React from "react";
import { useConfigs, useUpdateConfig, useValidateLLM } from "../hooks/use-config";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/utils";

export function GlobalModelConfig() {
	const { data: configs, isLoading } = useConfigs();
	const updateConfig = useUpdateConfig();
	const validateLLM = useValidateLLM();

	const [isEditing, setIsEditing] = React.useState(false);
	const [showKeys, setShowKeys] = React.useState(false);
	const [isValidated, setIsValidated] = React.useState<boolean | null>(null);

	// Form state
	const [activeProvider, setActiveProvider] = React.useState("openai");
	const [modelName, setModelName] = React.useState("");
	const [apiKey, setApiKey] = React.useState("");

	React.useEffect(() => {
		if (configs) {
			setTimeout(() => {
				setActiveProvider(
					(configs.find((c) => c.key === "LLM_ACTIVE_PROVIDER")?.value as string) || "openai",
				);
				setModelName(
					(configs.find((c) => c.key === "LLM_ACTIVE_MODEL_NAME")?.value as string) || "",
				);
				setApiKey((configs.find((c) => c.key === "LLM_API_KEY")?.value as string) || "");
			}, 0);
		}
	}, [configs]);

	const inputClass =
		isValidated === false
			? "bg-black-50 border-red-300 text-black-500 focus-visible:ring-red-300"
			: "bg-black-50 border-black-50 text-black-500";

	const handleVerify = async () => {
		if (!apiKey || !modelName) return;
		try {
			await validateLLM.mutateAsync({
				provider: activeProvider,
				model_name: modelName,
				api_key: apiKey,
			});
			setIsValidated(true);
			toast.success("Connection successful!");
		} catch (error) {
			setIsValidated(false);
			toast.error(getErrorMessage(error, "Failed to validate AI configuration."));
		}
	};

	const handleSave = async () => {
		try {
			await updateConfig.mutateAsync({
				key: "LLM_ACTIVE_PROVIDER",
				data: { value: activeProvider },
			});
			await updateConfig.mutateAsync({ key: "LLM_ACTIVE_MODEL_NAME", data: { value: modelName } });
			await updateConfig.mutateAsync({ key: "LLM_API_KEY", data: { value: apiKey } });

			setIsEditing(false);
			toast.success("AI Model Configuration saved successfully!");
		} catch (error) {
			toast.error(getErrorMessage(error, "Failed to save AI configuration."));
			console.error("Save failed", error);
		}
	};

	if (isLoading) {
		return <div className="p-4 text-center text-sm text-gray-500">Loading AI configuration...</div>;
	}

	return (
		<div className="flex flex-col gap-4 w-full">
			<div className="flex flex-col gap-6 border border-black-50 rounded-lg p-4 bg-white">
				{/* Top Part: Title and Edit Button */}
				<div className="flex justify-between items-start">
					<div className="flex flex-col gap-1">
						<h3 className="text-base font-medium text-black-500">Global AI Model Configuration</h3>
						<p className="text-sm text-black-300">
							Configure the default LLM provider, active model, and API key for the chatbot.
						</p>
					</div>
					<div className="flex items-center gap-2">
						{isEditing ? (
							<>
								<Button
									variant="ghost"
									className="text-black-500 hover:text-black-600 hover:bg-zinc-100 px-5 rounded-lg font-medium"
									onClick={() => {
										setIsEditing(false);
										setIsValidated(null);
										// Reset state
										if (configs) {
											setActiveProvider(
												(configs.find((c) => c.key === "LLM_ACTIVE_PROVIDER")?.value as string) ||
													"openai",
											);
											setModelName(
												(configs.find((c) => c.key === "LLM_ACTIVE_MODEL_NAME")?.value as string) ||
													"",
											);
											setApiKey(
												(configs.find((c) => c.key === "LLM_API_KEY")?.value as string) || "",
											);
										}
									}}
									disabled={updateConfig.isPending || validateLLM.isPending}
								>
									Cancel
								</Button>
								{isValidated === true ? (
									<Button
										className="bg-blue-600 hover:bg-blue-700 text-white shadow-none px-5 rounded-lg font-medium"
										onClick={handleSave}
										disabled={updateConfig.isPending}
									>
										{updateConfig.isPending ? (
											<RiLoader4Line className="size-4.5 mr-2 animate-spin" />
										) : (
											<RiCheckLine className="size-4.5 mr-2" />
										)}
										Save
									</Button>
								) : (
									<Button
										variant="outline"
										className="border-blue-500 text-blue-500 hover:text-blue-600 hover:bg-blue-50 bg-transparent shadow-none px-5 rounded-lg font-medium"
										onClick={handleVerify}
										disabled={validateLLM.isPending || !apiKey || !modelName}
									>
										{validateLLM.isPending ? (
											<RiLoader4Line className="size-4.5 mr-2 animate-spin" />
										) : (
											<RiCheckLine className="size-4.5 mr-2" />
										)}
										Test Connection
									</Button>
								)}
							</>
						) : (
							<Button
								variant="outline"
								className="border-blue-500 text-blue-500 hover:text-blue-600 hover:bg-blue-50 bg-transparent shadow-none px-5 rounded-lg"
								onClick={() => setIsEditing(true)}
							>
								<RiEdit2Line className="size-4.5 mr-2" />
								Edit
							</Button>
						)}
					</div>
				</div>

				<div className="grid grid-cols-3 gap-6">
					<div className="flex flex-col gap-2">
						<span className="text-sm font-medium text-black-500">Active Provider</span>
						<Select
							value={activeProvider}
							onValueChange={(val) => {
								setActiveProvider(val ?? "");
								setIsValidated(null);
							}}
							disabled={!isEditing}
						>
							<SelectTrigger className={`w-full h-10 rounded-lg ${inputClass}`}>
								<SelectValue placeholder="Select provider" />
							</SelectTrigger>
							<SelectContent alignItemWithTrigger={false}>
								<SelectItem value="openai">OpenAI</SelectItem>
								<SelectItem value="deepseek">DeepSeek</SelectItem>
								<SelectItem value="gemini">Google Gemini</SelectItem>
							</SelectContent>
						</Select>
					</div>
					<div className="flex flex-col gap-2">
						<span className="text-sm font-medium text-black-500">Active Model Name</span>
						<Input
							type="text"
							disabled={!isEditing}
							value={modelName}
							placeholder="e.g. gpt-4o, deepseek-chat"
							onChange={(e) => {
								setModelName(e.target.value);
								setIsValidated(null);
							}}
							className={`w-full h-10 rounded-lg disabled:opacity-75 ${inputClass}`}
						/>
					</div>

					<div className="flex flex-col gap-2">
						<span className="text-sm font-medium text-black-500">API Key</span>
						<div className="relative">
							<Input
								type={showKeys ? "text" : "password"}
								disabled={!isEditing}
								value={apiKey}
								placeholder="Enter API Key..."
								onChange={(e) => {
									setApiKey(e.target.value);
									setIsValidated(null);
								}}
								className={`w-full h-10 rounded-lg disabled:opacity-75 pr-10 ${inputClass}`}
							/>
							<button
								type="button"
								className="absolute right-3 top-1/2 -translate-y-1/2 text-black-400 hover:text-black-600 disabled:opacity-50"
								onClick={() => setShowKeys(!showKeys)}
								disabled={!isEditing && !apiKey}
							>
								{showKeys ? <RiEyeOffLine className="size-4" /> : <RiEyeLine className="size-4" />}
							</button>
						</div>
					</div>
				</div>

				{isValidated === false && (
					<p className="text-xs text-red-400 mt-1">
						Validation failed. Ensure your API Key matches the active provider and model.
					</p>
				)}
			</div>
		</div>
	);
}
