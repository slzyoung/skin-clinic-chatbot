import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useConfigs, useUpdateConfig } from "./use-config";

export interface PendingSaveState {
	key: "GLOBAL_TOKEN_THRESHOLD" | "GLOBAL_TOKEN_LIMIT" | "TOKEN_LIMIT_SPKK" | "TOKEN_LIMIT_GP";
	title: string;
	description: string;
	value: string;
	setter: (val: boolean) => void;
}

export function useTokenConfigState() {
	const { data: configs, isLoading } = useConfigs();
	const updateConfig = useUpdateConfig();

	const isGlobalLimitActive =
		configs?.find((c) => c.key === "GLOBAL_TOKEN_LIMIT_ACTIVE")?.value === "true";
	const globalThreshold =
		configs?.find((c) => c.key === "GLOBAL_TOKEN_THRESHOLD")?.value || "1000000";
	const branchTokenLimit = configs?.find((c) => c.key === "GLOBAL_TOKEN_LIMIT")?.value || "3000000";
	const spdveLimit = configs?.find((c) => c.key === "TOKEN_LIMIT_SPKK")?.value || "500000";
	const gpPlusLimit = configs?.find((c) => c.key === "TOKEN_LIMIT_GP")?.value || "250000";

	const [isActive, setIsActive] = useState(true);

	// Per-field value states
	const [thresholdAmount, setThresholdAmount] = useState("1000000");
	const [branchAmount, setBranchAmount] = useState("3000000");
	const [spdveAmount, setSpdveAmount] = useState("500000");
	const [gpPlusAmount, setGpPlusAmount] = useState("250000");

	// Per-field edit states
	const [editingThreshold, setEditingThreshold] = useState(false);
	const [editingBranch, setEditingBranch] = useState(false);
	const [editingSpdve, setEditingSpdve] = useState(false);
	const [editingGpPlus, setEditingGpPlus] = useState(false);

	const [savingKey, setSavingKey] = useState<string | null>(null);
	const [showWarning, setShowWarning] = useState(false);
	const warningTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

	// Toggle Confirmation State
	const [toggleModalOpen, setToggleModalOpen] = useState(false);
	const [pendingToggleActive, setPendingToggleActive] = useState<boolean | null>(null);

	// Save Confirmation State
	const [saveModalOpen, setSaveModalOpen] = useState(false);
	const [pendingSave, setPendingSave] = useState<PendingSaveState | null>(null);

	// Sync state when configs load
	useEffect(() => {
		if (configs) {
			const timer = setTimeout(() => {
				setIsActive(isGlobalLimitActive);
				setThresholdAmount(globalThreshold);
				setBranchAmount(branchTokenLimit);
				setSpdveAmount(spdveLimit);
				setGpPlusAmount(gpPlusLimit);
			}, 0);
			return () => clearTimeout(timer);
		}
	}, [configs, isGlobalLimitActive, globalThreshold, branchTokenLimit, spdveLimit, gpPlusLimit]);

	const handleInitiateSave = (
		key: "GLOBAL_TOKEN_THRESHOLD" | "GLOBAL_TOKEN_LIMIT" | "TOKEN_LIMIT_SPKK" | "TOKEN_LIMIT_GP",
		title: string,
		description: string,
		value: string,
		setter: (val: boolean) => void,
	) => {
		setPendingSave({ key, title, description, value, setter });
		setSaveModalOpen(true);
	};

	const handleConfirmSave = async () => {
		if (!pendingSave) return;
		const { key, value, setter } = pendingSave;
		try {
			setSavingKey(key);
			await updateConfig.mutateAsync({ key, data: { value } });
			setter(false);
			setShowWarning(true);
			if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
			warningTimeoutRef.current = setTimeout(() => {
				setShowWarning(false);
			}, 5000);
			toast.success("Token configuration updated successfully!");
		} catch {
			toast.error("Failed to update token configuration.");
		} finally {
			setSavingKey(null);
			setPendingSave(null);
		}
	};

	const handleInitiateToggle = (checked: boolean) => {
		setPendingToggleActive(checked);
		setToggleModalOpen(true);
	};

	const handleConfirmToggle = () => {
		if (pendingToggleActive === null) return;
		const checked = pendingToggleActive;
		setIsActive(checked);

		setShowWarning(true);
		if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
		warningTimeoutRef.current = setTimeout(() => {
			setShowWarning(false);
		}, 5000);

		updateConfig.mutate(
			{ key: "GLOBAL_TOKEN_LIMIT_ACTIVE", data: { value: checked.toString() } },
			{
				onSuccess: () => {
					setPendingToggleActive(null);
					toast.success(`Global token configuration ${checked ? "activated" : "deactivated"}!`);
				},
				onError: () => {
					setIsActive(!checked);
					setPendingToggleActive(null);
				},
			},
		);
	};

	return {
		isLoading,
		isPending: updateConfig.isPending,
		isActive,
		thresholdAmount,
		setThresholdAmount,
		globalThreshold,
		editingThreshold,
		setEditingThreshold,
		branchAmount,
		setBranchAmount,
		branchTokenLimit,
		editingBranch,
		setEditingBranch,
		spdveAmount,
		setSpdveAmount,
		spdveLimit,
		editingSpdve,
		setEditingSpdve,
		gpPlusAmount,
		setGpPlusAmount,
		gpPlusLimit,
		editingGpPlus,
		setEditingGpPlus,
		savingKey,
		showWarning,
		toggleModalOpen,
		setToggleModalOpen,
		pendingToggleActive,
		setPendingToggleActive,
		saveModalOpen,
		setSaveModalOpen,
		pendingSave,
		setPendingSave,
		handleInitiateToggle,
		handleConfirmToggle,
		handleInitiateSave,
		handleConfirmSave,
	};
}
