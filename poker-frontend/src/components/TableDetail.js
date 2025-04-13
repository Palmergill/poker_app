// src/components/TableDetail.js
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import pokerApi from '../api/poker';

const TableDetail = () => {
  const { id } = useParams();
  const [table, setTable] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTable = async () => {
      try {
        const response = await pokerApi.getTable(id);
        setTable(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching table:', error);
        setLoading(false);
      }
    };

    fetchTable();
  }, [id]);

  if (loading) {
    return <div>Loading table details...</div>;
  }

  if (!table) {
    return <div>Table not found</div>;
  }

  return (
    <div className="table-detail">
      <h2>{table.name}</h2>
      <div className="table-info">
        <p>Max Players: {table.max_players}</p>
        <p>Small Blind: ${table.small_blind}</p>
        <p>Big Blind: ${table.big_blind}</p>
        <p>Min Buy-in: ${table.min_buy_in}</p>
        <p>Max Buy-in: ${table.max_buy_in}</p>
      </div>
      <div className="poker-table">
        {/* This is where you would render the actual poker table UI */}
        <div className="poker-table-visual">
          <div className="table-center">
            <p>Pot: $0</p>
            <div className="community-cards">
              {/* Community cards would go here */}
            </div>
          </div>
          <div className="seats">
            {/* Generate seats in a circle */}
            {Array.from({ length: table.max_players }).map((_, index) => (
              <div key={index} className="seat">
                <div className="seat-number">{index + 1}</div>
                <div className="player-space">Empty</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TableDetail;