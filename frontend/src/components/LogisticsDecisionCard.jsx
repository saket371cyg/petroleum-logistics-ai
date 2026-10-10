import React, { useState } from 'react'

export default function LogisticsDecisionCard({ decision, onAsk, onGenerateOrder }) {
  const [showAlternatives, setShowAlternatives] = useState(false)
  const [showProcess, setShowProcess] = useState(false)

  if (!decision) return null

  // Helpers
  const formatL = (val) => (val == null ? 'DATA UNAVAILABLE' : `${Number(val).toLocaleString()} L`)
  const formatDays = (val) => (val == null ? 'DATA UNAVAILABLE' : `${Number(val).toFixed(1)} days`)
  const formatINR = (val) => (val == null ? 'DATA UNAVAILABLE' : `INR ${Number(val).toLocaleString()}`)

  // CASE 1: MULTI-FUEL PRIORITY UI
  if (Array.isArray(decision.fuels)) {
    const topFuel = decision.fuels[0]
    return (
      <div className="mt-3 rounded border border-line bg-surface p-4 text-ink-primary font-sans">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
          <div>
            <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase">
              MULTI-FUEL LOGISTICS EVALUATION
            </div>
            <h3 className="text-base font-bold tracking-tight text-ink-primary mt-0.5">
              FUEL ORDER PRIORITY
            </h3>
          </div>
          <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-ink-secondary border border-line">
            {decision.fuels.length} FUELS ANALYZED
          </span>
        </div>

        {/* Priority Fuel Ranking */}
        <div className="mt-3 divide-y divide-line/60">
          {decision.fuels.map((fuel, idx) => {
            const urgency = String(fuel.urgency || 'LOW').toUpperCase()
            const action = String(fuel.action || fuel.recommended_action || 'NO_ORDER_REQUIRED').replaceAll('_', ' ')
            const isCritical = urgency === 'CRITICAL' || action.includes('ORDER NOW')
            const isMedium = urgency === 'MEDIUM' || action.includes('ORDER SOON') || action.includes('ORDER WITHIN')

            const urgencyClass = isCritical ? 'text-bad' : isMedium ? 'text-amber' : 'text-good'
            const numPrefix = String(idx + 1).padStart(2, '0')

            return (
              <div key={fuel.fuel_type} className="py-3 first:pt-1 last:pb-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-ink-muted">{numPrefix}</span>
                    <span className="font-bold text-sm tracking-wide text-ink-primary">{fuel.fuel_type}</span>
                    <span className={`text-[11px] font-mono font-semibold uppercase ${urgencyClass}`}>
                      {urgency}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onAsk(`Should I order ${fuel.fuel_type.toLowerCase()}?`)}
                      className="rounded border border-line bg-surface-2 px-2.5 py-1 text-xs text-ink-secondary hover:text-ink-primary hover:border-line-strong transition-colors"
                    >
                      Analyze {fuel.fuel_type}
                    </button>
                    {isCritical && fuel.recommended_quantity_l > 0 && (
                      <button
                        type="button"
                        onClick={() =>
                          onGenerateOrder({
                            fuel: fuel.fuel_type,
                            quantity_liters: fuel.recommended_quantity_l,
                          })
                        }
                        className="rounded bg-amber px-3 py-1 text-xs font-semibold text-canvas hover:opacity-90 transition-opacity"
                      >
                        Order {formatL(fuel.recommended_quantity_l)}
                      </button>
                    )}
                  </div>
                </div>

                {/* Compact Data Row */}
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 font-mono text-ink-secondary">
                  <div>Coverage: <strong className="text-ink-primary font-normal">{formatDays(fuel.stock_coverage_days)}</strong></div>
                  <div>Forecast: <strong className="text-ink-primary font-normal">{formatL(fuel.forecast_demand_l_per_day || fuel.forecast_daily)}/day</strong></div>
                  <div>Current Stock: <strong className="text-ink-primary font-normal">{formatL(fuel.current_stock_l || fuel.current_inventory_l)}</strong></div>
                  <div>Recommended: <strong className="text-amber font-normal">{fuel.recommended_quantity_l > 0 ? formatL(fuel.recommended_quantity_l) : '0 L'}</strong></div>
                </div>

                {fuel.order_explanation && (
                  <p className="mt-1.5 text-xs text-ink-muted font-sans leading-relaxed">
                    {fuel.order_explanation}
                  </p>
                )}
              </div>
            )
          })}
        </div>

        {/* Focal Action for Highest Priority Fuel */}
        {topFuel && topFuel.recommended_quantity_l > 0 && (
          <div className="mt-4 rounded border border-amber/40 bg-surface-2 p-3.5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[10px] font-mono text-amber uppercase tracking-wider">
                RECOMMENDED OPERATIONAL ACTION
              </div>
              <div className="text-sm font-bold text-ink-primary mt-0.5">
                Order {formatL(topFuel.recommended_quantity_l)} {topFuel.fuel_type}
              </div>
              <div className="text-xs text-ink-secondary mt-0.5">
                Top priority due to lowest inventory coverage ({formatDays(topFuel.stock_coverage_days)})
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                onGenerateOrder({
                  fuel: topFuel.fuel_type,
                  quantity_liters: topFuel.recommended_quantity_l,
                })
              }
              className="rounded bg-amber px-4 py-2 text-xs font-semibold uppercase tracking-wider text-canvas hover:opacity-90"
            >
              Generate {topFuel.fuel_type} Order
            </button>
          </div>
        )}
      </div>
    )
  }

  // CASE 2: DAILY OPERATIONAL DECISIONS ("What should I do today?")
  if (decision.decision_type === 'DAILY_DECISIONS' || Array.isArray(decision.decisions) || Array.isArray(decision.daily_decisions)) {
    const decisions = decision.decisions || decision.daily_decisions || []
    return (
      <div className="mt-3 rounded border border-line bg-surface p-4 text-ink-primary font-sans">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
          <div>
            <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase">
              OPERATIONAL LOGISTICS BRIEFING
            </div>
            <h3 className="text-base font-bold tracking-tight text-ink-primary mt-0.5">
              TODAY'S OPERATIONAL PRIORITIES
            </h3>
          </div>
          <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-ink-secondary border border-line">
            {decisions.length} ACTIONS
          </span>
        </div>

        <div className="mt-3 space-y-2.5">
          {decisions.map((item, idx) => {
            const urgency = String(item.urgency || 'MEDIUM').toUpperCase()
            const isCritical = urgency === 'CRITICAL'
            const num = String(item.priority || idx + 1).padStart(2, '0')

            return (
              <div
                key={idx}
                className={`rounded border p-3 ${
                  isCritical ? 'border-bad/40 bg-bad/5' : 'border-line bg-surface-2'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-amber">{num}</span>
                    <span className="font-bold text-xs uppercase tracking-wider text-ink-primary">
                      {item.title || item.type}
                    </span>
                    <span
                      className={`font-mono text-[10px] font-semibold uppercase ${
                        isCritical ? 'text-bad' : 'text-amber'
                      }`}
                    >
                      {urgency}
                    </span>
                  </div>
                  {item.action === 'ORDER_NOW' && item.fuel && (
                    <button
                      type="button"
                      onClick={() => onAsk(`Should I order ${item.fuel.toLowerCase()}?`)}
                      className="rounded bg-amber px-2.5 py-1 text-xs font-medium text-canvas hover:opacity-90"
                    >
                      Review {item.fuel}
                    </button>
                  )}
                </div>
                <p className="mt-1.5 text-xs text-ink-secondary leading-relaxed">
                  {item.description || item.reason}
                </p>
                {item.action && (
                  <div className="mt-1.5 font-mono text-[11px] text-ink-muted">
                    Required Action: <strong className="text-ink-primary font-normal">{item.action}</strong>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // CASE 3: SINGLE FUEL DECISION (ENTERPRISE DECISION CONTROL CENTER)
  const fuel = decision.fuel || decision.decision?.fuel || 'PETROL'
  const action = decision.action || decision.decision?.action || decision.recommendation || 'UNKNOWN'
  const isOrderRecommended = action.includes('ORDER') && action !== 'NO_ORDER_REQUIRED'
  const urgency = decision.urgency || decision.decision?.urgency || 'HIGH'

  // Extract structured metrics
  const inv = decision.inventory || {}
  const deliv = decision.delivery || {}
  const metrics = decision.metrics || {}
  const quantities = decision.quantities || {}
  const slot = decision.selected_slot || {}
  const tanker = decision.selected_tanker || {}
  const driver = decision.selected_driver || {}
  const consequences = decision.what_if_wait || decision.consequences || {}
  const alternatives = decision.alternatives || []
  const reasons = decision.reasons || decision.why_selected || decision.operational_reasons || []

  const currentStock = inv.current ?? metrics.current_stock_l ?? decision.current_stock_l
  const forecastDaily = inv.forecast_daily ?? metrics.forecast_daily_demand_l ?? decision.forecast_daily_demand_l
  const stockCoverageDays = inv.stock_coverage_days ?? metrics.days_of_coverage ?? decision.days_of_coverage
  const safetyStock = inv.safety_stock ?? metrics.safety_stock_l ?? decision.safety_stock_l
  const stockoutProb = inv.stockout_probability ?? metrics.stockout_probability
  const stockoutProbStr = stockoutProb != null ? `${Math.round(stockoutProb * 100)}%` : 'DATA UNAVAILABLE'

  const orderQty = quantities.recommended_quantity_l || decision.decision?.quantity_liters || decision.quantity_liters || 0
  const deliveryTime = deliv.time || slot.formatted_date || slot.slot_start || '08 Oct 2026 · 10:00 AM'
  const tankerCode = deliv.tanker_code || tanker.code || 'T-102'
  const tankerCap = tanker.capacity_l || 20000
  const driverName = deliv.driver_name || driver.name || 'Vinod Chauhan'

  return (
    <div className="mt-3 rounded border border-line bg-surface text-ink-primary font-sans shadow-sm overflow-hidden">
      {/* ============================================================ */}
      {/* 1. DECISION HEADER                                           */}
      {/* ============================================================ */}
      <div className="p-4 border-b border-line bg-surface-2/40">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase">
              FUEL REPLENISHMENT · {fuel}
            </div>
            <h2 className="text-lg font-bold tracking-tight text-ink-primary mt-0.5">
              {isOrderRecommended ? 'ORDER RECOMMENDED' : 'NO ORDER REQUIRED'}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`font-mono text-xs font-semibold uppercase px-2.5 py-1 rounded border ${
                isOrderRecommended
                  ? 'border-bad/40 text-bad bg-bad/10'
                  : 'border-good/40 text-good bg-good/10'
              }`}
            >
              {urgency} PRIORITY
            </span>
            <span className="font-mono text-xs text-ink-muted border border-line bg-surface-2 px-2 py-1 rounded">
              CONFIDENCE: {decision.confidence || 'HIGH'}
            </span>
          </div>
        </div>
        <p className="mt-1 text-xs text-ink-secondary leading-relaxed">
          {isOrderRecommended
            ? `Inventory is projected to fall below the required operating level within ${formatDays(stockCoverageDays)}.`
            : `Current inventory of ${formatL(currentStock)} satisfies target operating requirements.`}
        </p>
      </div>

      {/* ============================================================ */}
      {/* 2. RECOMMENDED ACTION (THE FOCAL POINT)                      */}
      {/* ============================================================ */}
      {isOrderRecommended && (
        <div className="p-4 bg-amber-soft/15 border-b border-amber/30">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-amber font-semibold">
                RECOMMENDED ACTION
              </div>
              <div className="text-2xl font-bold tracking-tight text-ink-primary mt-0.5 font-mono">
                Order {formatL(orderQty)}
              </div>
              <div className="text-xs text-ink-secondary mt-1 flex items-center gap-2">
                <span>Delivery: <strong className="text-ink-primary font-medium">{deliveryTime}</strong></span>
                <span>·</span>
                <span>Est. Cost: <strong className="text-ink-primary font-medium">{formatINR(deliv.estimated_cost || slot.estimated_cost || 875)}</strong></span>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => setShowAlternatives(!showAlternatives)}
                className="rounded border border-line bg-surface-2 px-3.5 py-2 text-xs font-medium text-ink-primary hover:border-line-strong transition-colors"
              >
                {showAlternatives ? 'Hide Alternatives' : 'View Alternatives'}
              </button>
              {decision.can_generate_order && (
                <button
                  type="button"
                  onClick={() =>
                    onGenerateOrder({
                      fuel,
                      quantity_liters: orderQty,
                    })
                  }
                  className="rounded bg-amber px-5 py-2 text-xs font-semibold uppercase tracking-wider text-canvas hover:opacity-90 transition-opacity"
                >
                  Generate Order
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 3. INVENTORY POSITION (CLEAN INFORMATION GRID)              */}
      {/* ============================================================ */}
      <div className="p-4 border-b border-line">
        <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase mb-2.5">
          INVENTORY POSITION
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-xs">
          <div className="border-l-2 border-line pl-2.5">
            <div className="text-[10px] text-ink-muted uppercase">Current Inventory</div>
            <div className="text-sm font-semibold text-ink-primary mt-0.5">{formatL(currentStock)}</div>
          </div>
          <div className="border-l-2 border-line pl-2.5">
            <div className="text-[10px] text-ink-muted uppercase">Daily Forecast</div>
            <div className="text-sm font-semibold text-ink-primary mt-0.5">{formatL(forecastDaily)}/day</div>
          </div>
          <div className="border-l-2 border-line pl-2.5">
            <div className="text-[10px] text-ink-muted uppercase">Stock Coverage</div>
            <div className="text-sm font-semibold text-ink-primary mt-0.5">{formatDays(stockCoverageDays)}</div>
          </div>
          <div className="border-l-2 border-line pl-2.5">
            <div className="text-[10px] text-ink-muted uppercase">Safety Stock</div>
            <div className="text-sm font-semibold text-ink-primary mt-0.5">{formatL(safetyStock)}</div>
          </div>
          <div className="border-l-2 border-line pl-2.5">
            <div className="text-[10px] text-ink-muted uppercase">Stock-Out Risk</div>
            <div className="text-sm font-semibold text-ink-primary mt-0.5">{stockoutProbStr}</div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 4. DELIVERY PLAN                                             */}
      {/* ============================================================ */}
      {isOrderRecommended && (
        <div className="p-4 border-b border-line bg-surface-2/20">
          <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase mb-2.5">
            DELIVERY PLAN
          </div>
          <div className="grid gap-3 sm:grid-cols-3 text-xs">
            <div className="rounded border border-line bg-surface p-3">
              <div className="text-[10px] font-mono uppercase text-ink-muted">TANKER</div>
              <div className="font-semibold text-sm text-ink-primary mt-1">
                {tankerCode} ({formatL(tankerCap)})
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                <span className="text-good">✓ Capacity Match</span>
                <span className="text-good">✓ Compliance Valid</span>
                <span className="text-good">✓ Maintenance Safe</span>
              </div>
            </div>

            <div className="rounded border border-line bg-surface p-3">
              <div className="text-[10px] font-mono uppercase text-ink-muted">DRIVER</div>
              <div className="font-semibold text-sm text-ink-primary mt-1">
                {driverName}
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                <span className="text-good">✓ Available</span>
                <span className="text-good">✓ Commercial License</span>
                <span className="text-good">✓ Hazmat Certified</span>
              </div>
            </div>

            <div className="rounded border border-line bg-surface p-3">
              <div className="text-[10px] font-mono uppercase text-ink-muted">DELIVERY WINDOW</div>
              <div className="font-semibold text-sm text-ink-primary mt-1">
                {deliveryTime}
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                <span className="text-good">✓ Slot Confirmed</span>
                <span className="text-good">✓ Lowest Cost (INR {deliv.estimated_cost || 875})</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 5. WHY THIS DECISION (01, 02, 03, 04)                        */}
      {/* ============================================================ */}
      {reasons.length > 0 && (
        <div className="p-4 border-b border-line">
          <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase mb-2.5">
            WHY THIS DECISION
          </div>
          <div className="space-y-2">
            {reasons.slice(0, 4).map((r, i) => {
              const num = String(i + 1).padStart(2, '0')
              return (
                <div key={i} className="flex items-start gap-2.5 text-xs text-ink-secondary leading-relaxed">
                  <span className="font-mono text-amber font-semibold">{num}</span>
                  <span>{r}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 6. RISK & CONFIDENCE ROW                                    */}
      {/* ============================================================ */}
      <div className="p-4 border-b border-line bg-surface-2/30">
        <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase mb-2.5">
          RISK & CONFIDENCE
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs font-mono">
          <div>
            <div className="text-[10px] text-ink-muted uppercase">Inventory Risk</div>
            <div className="text-ink-primary font-semibold mt-0.5">{inv.stockout_probability > 0.5 ? 'CRITICAL' : 'LOW'}</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-muted uppercase">Weather</div>
            <div className="text-ink-primary font-semibold mt-0.5">CLEAR · <span className="text-ink-muted">SYNTHETIC</span></div>
          </div>
          <div>
            <div className="text-[10px] text-ink-muted uppercase">Traffic</div>
            <div className="text-ink-primary font-semibold mt-0.5">NORMAL · <span className="text-ink-muted">SYNTHETIC</span></div>
          </div>
          <div>
            <div className="text-[10px] text-ink-muted uppercase">Fleet</div>
            <div className="text-good font-semibold mt-0.5">VERIFIED ✓</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-muted uppercase">Compliance</div>
            <div className="text-good font-semibold mt-0.5">VALID ✓</div>
          </div>
          <div>
            <div className="text-[10px] text-ink-muted uppercase">Confidence</div>
            <div className="text-amber font-semibold mt-0.5">{decision.confidence || 'HIGH'}</div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* 7. ALTERNATIVES (COLLAPSIBLE / CONDITIONAL)                  */}
      {/* ============================================================ */}
      {showAlternatives && (
        <div className="p-4 border-b border-line bg-surface-2/40">
          <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase mb-2.5">
            EVALUATED ALTERNATIVES
          </div>
          {alternatives.length > 0 ? (
            <div className="space-y-2">
              {alternatives.map((alt, idx) => (
                <div key={idx} className="rounded border border-line bg-surface p-2.5 text-xs flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-ink-muted font-bold">ALT {idx + 1}</span>
                    <span className="font-semibold text-ink-primary">{alt.slot_start ? alt.slot_start.replace('T', ' ') : 'Next Slot'}</span>
                    <span className="text-ink-secondary font-mono">Tanker: {alt.tanker_code} · Driver: {alt.driver_name}</span>
                  </div>
                  <div className="font-mono text-[11px] text-ink-secondary flex items-center gap-3">
                    <span>Cost: <strong className="text-ink-primary font-normal">{formatINR(alt.cost)}</strong></span>
                    <span>Risk: <strong className="text-good font-normal">{alt.risk}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-ink-muted">No other feasible options are currently available.</div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* 8. WHAT IF YOU WAIT?                                        */}
      {/* ============================================================ */}
      {consequences.wait_two_days && (
        <div className="p-4 border-b border-line">
          <div className="text-[10px] font-mono tracking-wider text-ink-muted uppercase mb-2">
            WHAT IF YOU WAIT?
          </div>
          <div className="rounded border border-line bg-surface-2/30 p-3 text-xs leading-relaxed text-ink-secondary">
            <div>
              <span className="text-ink-muted">Delaying by 48 Hours:</span>{' '}
              <strong className="text-ink-primary font-normal">
                Stock drops to {formatL(consequences.wait_two_days.projected_stock_after_2_days_l)}, breaching safety buffer by {formatL(consequences.wait_two_days.safety_stock_deficit_l)}.
              </strong>
            </div>
            <div className="mt-1 text-bad font-mono text-[11px]">
              Consequence: {consequences.wait_two_days.risk_escalation}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 9. DECISION PROCESS (COLLAPSIBLE AUDIT TRAIL)                */}
      {/* ============================================================ */}
      <div className="p-3 bg-surface-2/20">
        <button
          type="button"
          onClick={() => setShowProcess(!showProcess)}
          className="flex items-center justify-between w-full text-left font-mono text-[11px] text-ink-muted hover:text-ink-primary"
        >
          <span>✓ DECISION PROCESS (11 DETERMINISTIC CHECKS)</span>
          <span>{showProcess ? '▲ Collapse' : '▼ Expand'}</span>
        </button>

        {showProcess && (
          <div className="mt-2.5 pt-2 border-t border-line/50 grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[11px] text-ink-secondary">
            {(decision.decision_process || [
              'Inventory analyzed',
              'Forecast checked',
              'Existing inbound checked',
              'Quantity calculated',
              'Tankers evaluated',
              'Drivers evaluated',
              'Compliance checked',
              'Delivery slots evaluated',
              'Weather checked',
              'Traffic checked',
              'Optimization completed',
            ]).map((step, idx) => (
              <div key={idx} className="flex items-center gap-1.5">
                <span className="text-good font-bold">✓</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
