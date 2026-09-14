import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RiCheckLine, RiEdit2Line, RiLoader4Line } from "@remixicon/react";

interface TokenLimitRowProps {
	label: string;
	value: string;
	onChange: (val: string) => void;
	isEditing: boolean;
	onEdit: () => void;
	onCancel: () => void;
	onSave: () => void;
	isSaving: boolean;
	placeholder?: string;
	suffix?: string;
}

export function TokenLimitRow({
	label,
	value,
	onChange,
	isEditing,
	onEdit,
	onCancel,
	onSave,
	isSaving,
	placeholder = "1000000",
	suffix = "per month",
}: TokenLimitRowProps) {
	return (
		<div className="flex flex-col gap-1.5">
			<span className="text-sm text-zinc-600">{label}</span>
			<div className="flex items-center gap-4">
				<div className="relative w-64">
					<Input
						type="number"
						disabled={!isEditing}
						value={value}
						placeholder={placeholder}
						onChange={(e) => onChange(e.target.value)}
						className="w-full bg-[#f0f0f0] border-gray-200 text-zinc-800 h-10 rounded-lg pr-20 disabled:opacity-80 focus-visible:ring-blue-500"
					/>
					{suffix && (
						<span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-zinc-400 pointer-events-none select-none">
							{suffix}
						</span>
					)}
				</div>
				{isEditing ? (
					<div className="flex items-center gap-2">
						<Button
							type="button"
							variant="outline"
							className="border-gray-200 bg-white text-zinc-700 hover:bg-zinc-50 rounded-lg px-4 font-medium h-10 text-sm transition-colors cursor-pointer shadow-none"
							onClick={onCancel}
							disabled={isSaving}
						>
							Cancel
						</Button>
						<Button
							type="button"
							className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 font-medium h-10 text-sm transition-colors cursor-pointer shadow-none disabled:opacity-50"
							onClick={onSave}
							disabled={isSaving || !value}
						>
							{isSaving ? (
								<RiLoader4Line className="size-4 animate-spin mr-1" />
							) : (
								<RiCheckLine className="size-4 mr-1" />
							)}
							Save
						</Button>
					</div>
				) : (
					<Button
						type="button"
						variant="outline"
						className="border-gray-200 bg-white text-zinc-700 hover:bg-zinc-50 rounded-lg px-4 h-10 text-sm font-medium transition-colors cursor-pointer shadow-none gap-1.5"
						onClick={onEdit}
					>
						<RiEdit2Line className="size-4 text-zinc-500" />
						Edit
					</Button>
				)}
			</div>
		</div>
	);
}
