// src/components/TableList.js
import React, { useState, useEffect } from 'react';
import pokerApi from '../api/poker';
import { Link } from 'react-router-dom';

const TableList = () => {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const response = await pokerApi.getTables();
        setTables(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching tables:', error);
        setLoading(false);
      }
    };

    fetchTables();
  }, []);

  if (loading) {
    return <div>Loading tables...</div>;
  }

  return (
    <div className="table-list">
      <h2>Poker Tables</h2>
      {tables.length === 0 ? (
        <p>No tables available</p>
      ) : (
        <ul>
          {tables.map(table => (
            <li key={table.id}>
              <Link to={`/tables/${table.id}`}>
                {table.name} - Small Blind: ${table.small_blind}, Big Blind: ${table.big_blind}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TableList;