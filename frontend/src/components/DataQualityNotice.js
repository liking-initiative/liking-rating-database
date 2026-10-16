import React from 'react';
import { Alert } from 'antd';

// Some datasets carry defects inherited from the source compilation, which
// cannot be repaired here and are declared instead (migrations 011, 017). The
// point of this banner is that nobody should have to discover the problem
// from their own results.
const FLAGS = {
  placeholder_items: {
    type: 'warning',
    message: 'This dataset has unlabelled items',
  },
  coded_items: {
    type: 'info',
    message: 'Some items in this dataset have no readable name',
  },
  inferred_key: {
    type: 'info',
    message: 'Item names in this dataset were inferred from the data',
  },
  unidentified_items: {
    type: 'warning',
    message: 'Which food each rating refers to is unknown',
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
