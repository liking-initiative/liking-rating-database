import React from 'react';
import { Alert } from 'antd';

// Some datasets carry defects inherited from the source compilation — item
// labels that the original files simply did not contain. They cannot be
// repaired here, so they are declared instead (migration 011). The point of
// this banner is that nobody should have to discover the problem by finding
// an item called "nouniqueitem" in their own results.
const FLAGS = {
  placeholder_items: {
    type: 'warning',
    message: 'This dataset has unlabelled items',
  },
  coded_items: {
    type: 'info',
    message: 'Some items in this dataset have no readable name',
  },
};

const DataQualityNotice = ({ dataset }) => {
  const flag = dataset?.quality_flag && FLAGS[dataset.quality_flag];
  if (!flag) return null;
  return (
    <Alert
      type={flag.type}
      showIcon
      style={{ marginBottom: 16 }}
      message={flag.message}
      description={dataset.quality_note}
    />
  );
};

export default DataQualityNotice;
