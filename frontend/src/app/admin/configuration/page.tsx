import * as React from "react"
import { GlobalTokenConfig } from "./components/global-token-config"
import { BranchTokenTable } from "./components/branch-token-table"

export default function ConfigPage() {
  return (
    <div className="flex flex-col flex-1 min-h-full bg-white p-6">
      <div className="flex flex-col gap-6 w-full">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold text-black-500">Configuration</h1>
          <p className="text-sm text-black-300">Here is the overview data of the configuration</p>
        </div>

        {/* Content */}
        <div className="flex flex-col">
          <GlobalTokenConfig />
          <BranchTokenTable />
        </div>
      </div>
    </div>
  )
}
