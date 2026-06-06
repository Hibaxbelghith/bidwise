import { Plus, Trash2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';
import { FieldError, fieldClassName } from './OpportunityPostFields.jsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select.jsx';

const emptyLot = (index) => ({
  lot: `Lot ${index}`,
  objet: '',
  quantite: '',
  region: '',
  caution: '',
});

const TenderLotsEditor = ({ lots, error, onChange }) => {
  const updateLot = (index, field, value) => {
    onChange(lots.map((lot, lotIndex) => (lotIndex === index ? { ...lot, [field]: value } : lot)));
  };

  const addLot = () => onChange([...lots, emptyLot(lots.length + 1)]);
  const removeLot = (index) => onChange(lots.filter((_lot, lotIndex) => lotIndex !== index));

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-neutral-900">Lots</h2>
          <p className="mt-1 text-sm text-neutral-500">Add one or more lots when the tender is divided by article or lot.</p>
        </div>
        <Button type="button" variant="outline" className="h-10 rounded-xl" onClick={addLot}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add lot
        </Button>
      </div>
      <FieldError message={error} />

      <div className="mt-4 space-y-4">
        {lots.map((lot, index) => (
          <div key={`${lot.lot}-${index}`} className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-neutral-900">{lot.lot || `Lot ${index + 1}`}</p>
              {lots.length > 1 ? (
                <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={() => removeLot(index)}>
                  <Trash2 className="h-4 w-4 text-red-600" aria-hidden="true" />
                </Button>
              ) : null}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor={`lot-title-${index}`} className="text-xs font-semibold text-neutral-700">Lot title</label>
                <Input id={`lot-title-${index}`} value={lot.lot} onChange={(event) => updateLot(index, 'lot', event.target.value)} className={`mt-1 ${fieldClassName(false)}`} />
              </div>
              <div>
                <label htmlFor={`lot-quantity-${index}`} className="text-xs font-semibold text-neutral-700">Quantity</label>
                <Input id={`lot-quantity-${index}`} value={lot.quantite} onChange={(event) => updateLot(index, 'quantite', event.target.value)} className={`mt-1 ${fieldClassName(false)}`} />
              </div>
              <div className="md:col-span-2">
                <label htmlFor={`lot-object-${index}`} className="text-xs font-semibold text-neutral-700">Object</label>
                <Input id={`lot-object-${index}`} value={lot.objet} onChange={(event) => updateLot(index, 'objet', event.target.value)} className={`mt-1 ${fieldClassName(false)}`} />
              </div>
              <div>
                <label htmlFor={`lot-region-${index}`} className="text-xs font-semibold text-neutral-700">Execution region</label>
                <Select value={lot.region} onValueChange={(value) => updateLot(index, 'region', value)}>
                  <SelectTrigger id={`lot-region-${index}`} className={`mt-1 ${fieldClassName(false)}`}>
                    <SelectValue placeholder="Select region" />
                  </SelectTrigger>
                  <SelectContent>
                    {TUNISIAN_LOCATION_OPTIONS.map((item) => (
                      <SelectItem key={item} value={item}>{item}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label htmlFor={`lot-caution-${index}`} className="text-xs font-semibold text-neutral-700">Provisional guarantee amount</label>
                <Input id={`lot-caution-${index}`} value={lot.caution} onChange={(event) => updateLot(index, 'caution', event.target.value)} className={`mt-1 ${fieldClassName(false)}`} placeholder="1500 TND" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TenderLotsEditor;
